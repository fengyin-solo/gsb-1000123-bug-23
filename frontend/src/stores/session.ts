import { defineStore } from 'pinia'

export type SessionRole = 'admin' | 'viewer'

export interface SessionAccount {
  id: string
  name: string
  role: SessionRole
}

export const SESSION_STORAGE_KEY = 'lab-session-account-id'
export const SESSION_CHANGED_EVENT = 'lab:session-changed'

export const ACCOUNTS: SessionAccount[] = [
  { id: 'admin-001', name: '值班管理员', role: 'admin' },
  { id: 'viewer-001', name: '只读账号', role: 'viewer' },
]

const DEFAULT_ACCOUNT = ACCOUNTS[0]

function accountFromStorage(): SessionAccount {
  const accountId = window.localStorage.getItem(SESSION_STORAGE_KEY)
  return ACCOUNTS.find((account) => account.id === accountId) ?? DEFAULT_ACCOUNT
}

export const useSessionStore = defineStore('session', {
  state: () => {
    const account = accountFromStorage()
    return {
      account,
      operator: account.name,
      shiftLabel: '白班 08:00-20:00',
      scope: '实验室样品检测管理平台',
    }
  },
  getters: {
    isAdmin: (state) => state.account.role === 'admin',
    canOperate: (state) => state.account.role === 'admin',
    canManageReagent: (state) => state.account.role === 'admin',
  },
  actions: {
    setAccount(account: SessionAccount) {
      this.account = account
      this.operator = account.name
    },
    switchAccount(accountId: string) {
      const account = ACCOUNTS.find((item) => item.id === accountId) ?? DEFAULT_ACCOUNT
      this.setAccount(account)
      window.localStorage.setItem(SESSION_STORAGE_KEY, account.id)
      window.dispatchEvent(new CustomEvent(SESSION_CHANGED_EVENT))
    },
    syncFromStorage() {
      this.setAccount(accountFromStorage())
    },
  },
})

if (typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key === SESSION_STORAGE_KEY) {
      useSessionStore().syncFromStorage()
      window.dispatchEvent(new CustomEvent(SESSION_CHANGED_EVENT))
    }
  })
}
