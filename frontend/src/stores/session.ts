import { defineStore } from 'pinia'

import { request } from '@/api/client'

export interface AccountInfo {
  id: string
  name: string
  role: string
}

interface MeInfo {
  account: AccountInfo
  permissions: Record<string, boolean>
}

const STORAGE_KEY = 'operator-id'

/** 读取当前选中的账号 id；未选择时默认管理员，保证既有正常操作不失效。 */
function readStoredId(): string {
  return window.localStorage.getItem(STORAGE_KEY) || 'admin'
}

export const useSessionStore = defineStore('session', {
  state: () => ({
    operatorId: readStoredId(),
    operator: '值班管理员',
    role: 'admin',
    shiftLabel: '白班 08:00-20:00',
    scope: '实验室样品检测管理平台',
    accounts: [] as AccountInfo[],
    permissions: { reagentOperate: true } as Record<string, boolean>,
    loaded: false,
  }),
  getters: {
    // 权限以服务端 /accounts/me 的判定为准，前端只用来控制入口显隐；保存时后端还会再判一次。
    canOperateReagent: (state) => state.permissions.reagentOperate === true,
  },
  actions: {
    async loadAccounts() {
      try {
        const response = await request('/api/accounts')
        if (response.ok) {
          const payload = (await response.json()) as { items?: AccountInfo[] }
          this.accounts = payload.items ?? []
        }
      } finally {
        await this.refreshIdentity()
      }
    },
    async refreshIdentity() {
      try {
        const response = await request('/api/accounts/me')
        if (response.ok) {
          const info = (await response.json()) as MeInfo
          this.operatorId = info.account.id
          this.operator = info.account.name
          this.role = info.account.role
          this.permissions.reagentOperate = info.permissions['reagent:operate'] === true
          this.loaded = true
        }
      } catch {
        // 后端不可达时保持原状，不把页面误判成无权限
      }
    },
    /** 切换账号：只改 id 并向后端重新确认角色与权限，本地不自行推断权限。 */
    async switchAccount(id: string) {
      this.operatorId = id
      window.localStorage.setItem(STORAGE_KEY, id)
      await this.refreshIdentity()
    },
    setShift(label: string) {
      this.shiftLabel = label
    },
  },
})
