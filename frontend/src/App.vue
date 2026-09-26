<template>
  <div class="app-shell">
    <aside class="app-side">
      <h1 class="app-title">实验室样品检测管理平台</h1>
      <nav class="nav-list">
        <RouterLink v-for="item in navItems" :key="item.path" :to="item.path" class="nav-item">
          {{ item.label }}
        </RouterLink>
      </nav>
    </aside>
    <main class="app-main">
      <header class="app-head">
        <span class="head-desc">面向检测实验室的样品接收、检测任务分配、仪器校准、试剂耗材、结果报告与质量审核的综合管理后台。</span>
        <label class="account-switcher">
          当前账号
          <select :value="store.account.id" @change="switchAccount">
            <option v-for="account in accounts" :key="account.id" :value="account.id">
              {{ account.name }}（{{ account.role === 'admin' ? '管理员' : '只读' }}）
            </option>
          </select>
        </label>
      </header>
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { ACCOUNTS, useSessionStore } from '@/stores/session'

const store = useSessionStore()
const accounts = ACCOUNTS

function switchAccount(event: Event) {
  const target = event.target as HTMLSelectElement
  store.switchAccount(target.value)
}

const navItems = [{ label: "运营概览", path: "/" }, { label: "样品接收", path: "/sample" }, { label: "检测任务", path: "/task" }, { label: "仪器管理", path: "/instrument" }, { label: "校准记录", path: "/calibration" }, { label: "试剂耗材", path: "/reagent" }, { label: "检测结果", path: "/result" }, { label: "检测报告", path: "/report" }, { label: "质量控制", path: "/qc" }, { label: "偏离处理", path: "/deviation" }, { label: "样品留存", path: "/sample_storage" }, { label: "委托合同", path: "/contract" }, { label: "检测人员", path: "/staff" }, { label: "检测方法", path: "/method" }, { label: "环境监测", path: "/environment" }, { label: "客户申诉", path: "/complain" }, { label: "内审管理", path: "/audit" }, { label: "仪器维修", path: "/equipment_repair" }, { label: "体系文档", path: "/document" }]
</script>
