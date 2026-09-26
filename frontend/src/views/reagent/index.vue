<template>
  <section class="page" data-module="reagent">
    <header class="page-head">
      <div>
        <h2>试剂耗材管理</h2>
        <p class="page-desc">维护试剂耗材，围绕试剂编号、试剂名称、规格等级、生产厂家做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button
          v-if="session.canOperateReagent"
          class="btn primary"
          type="button"
          @click="openCreate"
        >登记试剂耗材</button>
        <button v-else class="btn primary" type="button" disabled>登记试剂耗材（无权限）</button>
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
          <th>归属</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td v-for="column in columns" :key="column">
            <RouterLink v-if="column === '试剂编号'" class="link" :to="`/reagent/${row.id}`">
              {{ row[column] ?? '—' }}
            </RouterLink>
            <template v-else>{{ row[column] ?? '—' }}</template>
          </td>
          <td>{{ ownerLabel(row) }}</td>
          <td class="row-actions">
            <template v-if="session.canOperateReagent">
              <button
                v-for="action in actions"
                :key="action"
                class="link"
                type="button"
                @click="runAction(action, row)"
              >
                {{ action }}
              </button>
            </template>
            <RouterLink v-else class="link" :to="`/reagent/${row.id}`">查看详情</RouterLink>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 2" class="empty-state">暂无试剂耗材数据，可先登记试剂耗材</td>
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
import { onMounted, ref } from 'vue'

import { readErrorDetail, request } from '@/api/client'
import { useSessionStore } from '@/stores/session'

type Row = Record<string, string | number | null>

const session = useSessionStore()
const ENDPOINT = '/api/reagent'
const columns = ["试剂编号", "试剂名称", "规格等级", "生产厂家", "有效期至", "存放位置", "领用人员", "使用状态"]
const actions = ["领用试剂", "登记用完", "标记过期"]
const statuses = ["在库", "已领用", "已用完", "已过期"]
const stats = [{"label": "在库试剂", "value": 0}, {"label": "已领用试剂", "value": 0}, {"label": "即将过期", "value": 0}]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

function ownerLabel(row: Row): string {
  const owner = row['归属人']
  const lastAction = row['最后动作']
  if (owner && lastAction) {
    return `${owner}（${lastAction}）`
  }
  return owner ? String(owner) : '未操作'
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '试剂耗材登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  // 入口判定：无权限账号在当前页根本点不到动作；即便切换账号后状态没刷新，保存时后端还会再判。
  if (!session.canOperateReagent) {
    errorMessage.value = '当前账号无权限执行试剂耗材动作，数据保持不变'
    return
  }
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action, version: row.version } }),
    })
    if (response.status === 403) {
      // 越权提交被后端拒绝：不修改本地任何数据，只提示并按服务端身份重判权限。
      errorMessage.value = await readErrorDetail(response, '无权限执行该操作，数据保持不变')
      await session.refreshIdentity()
      return
    }
    if (response.status === 409) {
      // 请求冲突（记录已被别人操作）：不覆盖归属，直接拉取服务器最新数据重绘。
      errorMessage.value = await readErrorDetail(response, '记录已被更新，请刷新后重试')
      await reload()
      return
    }
    const payload = (await response.json()) as { ok?: boolean; message?: string }
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '试剂耗材动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '试剂耗材操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
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

onMounted(reload)
</script>
