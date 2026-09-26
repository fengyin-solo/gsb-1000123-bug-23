<template>
  <section class="page" data-module="reagent">
    <header class="page-head">
      <div>
        <h2>试剂耗材管理</h2>
        <p class="page-desc">维护试剂耗材，围绕试剂编号、试剂名称、规格等级、生产厂家做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" :disabled="!store.canManageReagent" @click="openCreate">登记试剂耗材</button>
        <button class="btn" type="button" @click="exportRows">导出试剂耗材清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <table class="data-table">
      <thead>
        <tr>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">{{ row[column] ?? '—' }}</td>
          <td class="row-actions">
            <RouterLink class="link detail-link" :to="`/reagent/${row.id}`">详情</RouterLink>
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              :disabled="!canRunAction(action, row) || pendingActionId === String(row.id)"
              :title="actionTitle(action, row)"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 1" class="empty-state">暂无试剂耗材数据，可先登记试剂耗材</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条试剂耗材记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

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
const columns = COLUMNS
const actions = ACTIONS
const stats = [{ label: '在库试剂', value: 0 }, { label: '已领用试剂', value: 0 }, { label: '即将过期', value: 0 }]

const store = useSessionStore()
const rows = ref<ReagentRow[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)
const pendingActionId = ref('')
let actionController: AbortController | null = null

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  if (!store.canManageReagent) {
    errorMessage.value = '当前账号无权登记试剂耗材'
    return
  }
  errorMessage.value = '试剂耗材登记入口尚未接入审批流'
}

function canRunAction(action: ReagentAction, row: ReagentRow): boolean {
  return store.canManageReagent && actionAvailable(action, row)
}

function actionTitle(action: ReagentAction, row: ReagentRow): string {
  if (!store.canManageReagent) return '当前账号无权执行该操作'
  if (!actionAvailable(action, row)) return '当前状态不能执行该动作'
  return action
}

async function runAction(action: ReagentAction, row: ReagentRow) {
  errorMessage.value = ''
  if (!canRunAction(action, row)) {
    errorMessage.value = '当前账号无权执行该操作，或当前状态不能执行该动作'
    return
  }

  pendingActionId.value = String(row.id)
  actionController?.abort()
  actionController = new AbortController()
  try {
    const entry = await submitReagentAction(action, row, actionController.signal)
    Object.assign(row, entry)
  } catch (error) {
    if (error instanceof DOMException && error.name === 'AbortError') {
      return
    }
    if (error instanceof ActionConflictError) {
      errorMessage.value = error.message
      await reload()
    } else if (error instanceof ActionRejectedError || error instanceof Error) {
      errorMessage.value = error.message
    } else {
      errorMessage.value = '试剂耗材操作失败'
    }
  } finally {
    if (pendingActionId.value === String(row.id)) {
      pendingActionId.value = ''
    }
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (response.status === 403) {
      throw new Error('当前账号无权查看试剂耗材清单')
    }
    if (!response.ok) {
      throw new Error('试剂耗材列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '试剂耗材列表读取失败'
  }
}

function handleSessionChange() {
  actionController?.abort()
  pendingActionId.value = ''
  void reload()
}

onMounted(() => {
  window.addEventListener('pageshow', handleSessionChange)
  window.addEventListener(SESSION_CHANGED_EVENT, handleSessionChange)
  void reload()
})

onUnmounted(() => {
  window.removeEventListener('pageshow', handleSessionChange)
  window.removeEventListener(SESSION_CHANGED_EVENT, handleSessionChange)
})
</script>
