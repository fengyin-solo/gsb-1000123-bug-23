<template>
  <section class="page" data-module="reagent-detail">
    <header class="page-head">
      <div>
        <h2>试剂耗材详情</h2>
        <p class="page-desc">列表页与详情页使用同一份归属和状态数据；只有管理员可以保存状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回列表</button>
      </div>
    </header>

    <article v-if="entry" class="detail-card">
      <dl class="detail-grid">
        <template v-for="column in columns" :key="column">
          <dt>{{ column }}</dt>
          <dd :class="{ owner: column === '领用人员' }">{{ entry[column] || '—' }}</dd>
        </template>
        <dt>记录归属</dt>
        <dd class="owner">{{ entry.owner_name || entry['领用人员'] || '—' }}</dd>
        <dt>当前状态</dt>
        <dd>{{ entry.status ?? '—' }}</dd>
        <dt>数据版本</dt>
        <dd>{{ entry.version ?? 1 }}</dd>
      </dl>

      <div class="detail-actions">
        <button
          v-for="action in actions"
          :key="action"
          class="btn"
          type="button"
          :disabled="!canRunAction(action) || saving"
          :title="actionTitle(action)"
          @click="runAction(action)"
        >
          {{ action }}
        </button>
      </div>
    </article>

    <footer class="page-foot">
      <span v-if="!errorMessage">试剂耗材编号：{{ entryId }}</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { request } from '@/api/client'
import {
  ACTIONS,
  ActionConflictError,
  ActionRejectedError,
  COLUMNS,
  actionAvailable,
  submitReagentAction,
  type ReagentAction,
  type ReagentRow,
} from '@/views/reagent/reagent'
import { SESSION_CHANGED_EVENT, useSessionStore } from '@/stores/session'

const ENDPOINT = '/api/reagent'
const route = useRoute()
const router = useRouter()
const store = useSessionStore()

const entryId = String(route.params.id)
const columns = COLUMNS
const actions = ACTIONS
const entry = ref<ReagentRow | null>(null)
const errorMessage = ref('')
const saving = ref(false)
let actionController: AbortController | null = null

function canRunAction(action: ReagentAction): boolean {
  return Boolean(entry.value) && store.canManageReagent && actionAvailable(action, entry.value as ReagentRow)
}

function actionTitle(action: ReagentAction): string {
  if (!store.canManageReagent) return '当前账号无权执行该操作'
  if (entry.value && !actionAvailable(action, entry.value)) return '当前状态不能执行该动作'
  return action
}

function goBack() {
  void router.push('/reagent')
}

async function runAction(action: ReagentAction) {
  if (!entry.value || !canRunAction(action)) {
    errorMessage.value = '当前账号无权执行该操作，或当前状态不能执行该动作'
    return
  }

  const currentEntry = entry.value
  errorMessage.value = ''
  saving.value = true
  actionController?.abort()
  actionController = new AbortController()
  try {
    entry.value = await submitReagentAction(action, currentEntry, actionController.signal)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return
    }
    if (error instanceof ActionConflictError) {
      errorMessage.value = error.message
      await reload()
    } else if (error instanceof ActionRejectedError || error instanceof Error) {
      entry.value = currentEntry
      errorMessage.value = error.message
    } else {
      entry.value = currentEntry
      errorMessage.value = '试剂耗材操作失败'
    }
  } finally {
    saving.value = false
  }
}

async function reload() {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${entryId}`)
    if (response.status === 403) {
      throw new Error('当前账号无权查看该试剂耗材详情')
    }
    if (response.status === 404) {
      throw new Error(`试剂耗材 ${entryId} 不存在或已归档`)
    }
    if (!response.ok) {
      throw new Error('试剂耗材详情读取失败')
    }
    entry.value = await response.json()
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') return
    errorMessage.value = error instanceof Error ? error.message : '试剂耗材详情读取失败'
  }
}

function handleSessionChange() {
  actionController?.abort()
  saving.value = false
  void reload()
}

onMounted(() => {
  window.addEventListener('pageshow', handleSessionChange)
  window.addEventListener(SESSION_CHANGED_EVENT, handleSessionChange)
  void reload()
})

onUnmounted(() => {
  actionController?.abort()
  window.removeEventListener('pageshow', handleSessionChange)
  window.removeEventListener(SESSION_CHANGED_EVENT, handleSessionChange)
})
</script>

<style scoped>
.detail-card {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 16px;
}
.detail-grid {
  display: grid;
  grid-template-columns: 140px minmax(0, 1fr);
  gap: 10px 16px;
  margin: 0 0 18px;
}
.detail-grid dt { color: var(--muted); font-size: 13px; }
.detail-grid dd { margin: 0; font-size: 13px; }
.detail-grid .owner { font-weight: 600; }
.detail-actions { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
