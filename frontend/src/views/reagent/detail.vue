<template>
  <section class="page" data-module="reagent-detail">
    <header class="page-head">
      <div>
        <h2>试剂耗材详情</h2>
        <p class="page-desc">归属与状态以服务端记录为准；从列表页直接返回或切换账号后进入，都会重新拉取最新数据。</p>
      </div>
      <div class="page-actions">
        <button class="btn" type="button" @click="goBack">返回列表</button>
      </div>
    </header>

    <div v-if="errorMessage && !detail" class="empty-state">{{ errorMessage }}</div>

    <article v-else-if="detail" class="detail-card">
      <dl class="detail-grid">
        <template v-for="field in detailFields" :key="field">
          <dt>{{ field }}</dt>
          <dd>{{ detail[field] ?? '—' }}</dd>
        </template>
        <dt>状态</dt>
        <dd>{{ detail.status ?? '—' }}</dd>
        <dt>归属账号</dt>
        <dd>{{ detail['归属账号'] ?? '未操作' }}</dd>
        <dt>归属人</dt>
        <dd>{{ detail['归属人'] ?? '未操作' }}</dd>
        <dt>最后动作</dt>
        <dd>{{ detail['最后动作'] ?? '未操作' }}</dd>
        <dt>数据版本</dt>
        <dd>{{ detail.version ?? 0 }}</dd>
      </dl>

      <div class="detail-actions">
        <template v-if="session.canOperateReagent">
          <button
            v-for="action in actions"
            :key="action"
            class="btn primary"
            type="button"
            @click="runAction(action)"
          >
            {{ action }}
          </button>
        </template>
        <p v-else class="error-text">当前账号「{{ session.operator }}」为只读账号，不能领用、登记用完或标记过期。</p>
      </div>
      <p v-if="errorMessage" class="error-text">{{ errorMessage }}</p>
    </article>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { readErrorDetail, request } from '@/api/client'
import { useSessionStore } from '@/stores/session'

type Detail = Record<string, string | number | null>

const route = useRoute()
const router = useRouter()
const session = useSessionStore()

const ENDPOINT = '/api/reagent'
const detailFields = ["试剂编号", "试剂名称", "规格等级", "生产厂家", "有效期至", "存放位置", "领用人员", "使用状态"]
const actions = ["领用试剂", "登记用完", "标记过期"]

const detail = ref<Detail | null>(null)
const errorMessage = ref('')

function entryId(): number {
  return Number(route.params.id)
}

function goBack() {
  void router.push('/reagent')
}

async function runAction(action: string) {
  errorMessage.value = ''
  // 保存前再判一次：覆盖“切到无权限账号后仍停留在旧详情页”的场景。
  if (!session.canOperateReagent || !detail.value) {
    errorMessage.value = '当前账号无权限执行试剂耗材动作，归属与状态保持不变'
    return
  }
  const current = detail.value
  try {
    const response = await request(`${ENDPOINT}/${entryId()}/actions`, {
      method: 'POST',
      body: JSON.stringify({ values: { action, version: current.version ?? 0 } }),
    })
    if (response.status === 403) {
      // 越权提交：详情保持服务端原数据，只按后端结果重判权限，绝不本地改归属。
      errorMessage.value = await readErrorDetail(response, '无权限执行该操作，数据保持不变')
      await session.refreshIdentity()
      return
    }
    if (response.status === 409) {
      // 请求冲突：详情页持有的是旧版本，重新拉取，归属不会残留错误结论。
      errorMessage.value = await readErrorDetail(response, '记录已被更新，已为你刷新最新归属')
      await loadDetail()
      return
    }
    const payload = (await response.json()) as { ok?: boolean; message?: string }
    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || '试剂耗材动作未生效')
    }
    await loadDetail()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '试剂耗材操作失败'
  }
}

async function loadDetail() {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${entryId()}`)
    if (response.status === 404) {
      detail.value = null
      errorMessage.value = '该试剂耗材不存在或已归档'
      return
    }
    if (!response.ok) {
      throw new Error('试剂耗材详情读取失败')
    }
    // 详情只认服务端返回，避免直接返回后沿用旧内存里的错误归属。
    detail.value = (await response.json()) as Detail
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '试剂耗材详情读取失败'
  }
}

// 路由 id 变化（详情间跳转）和账号切换后都重新拉取，保证归属对得上。
watch(() => route.params.id, () => void loadDetail())
watch(() => session.operatorId, () => void loadDetail())

onMounted(loadDetail)
</script>
