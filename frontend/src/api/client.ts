/** 统一请求封装：拼后端地址、注入当前账号、抛网络错误、给页脚留一句可读的说明。 */
import { ACCOUNTS, SESSION_STORAGE_KEY } from '@/stores/session'

const API_BASE = import.meta.env.VITE_API_BASE ?? ''
const DEFAULT_ACCOUNT = ACCOUNTS[0]

function currentAccount() {
  const accountId = window.localStorage.getItem(SESSION_STORAGE_KEY) ?? DEFAULT_ACCOUNT.id
  return ACCOUNTS.find((account) => account.id === accountId) ?? DEFAULT_ACCOUNT
}

function sessionHeaders(): HeadersInit {
  const account = currentAccount()
  return {
    'X-Operator-Id': account.id,
    'X-Operator-Name': encodeURIComponent(account.name),
    'X-Operator-Role': account.role,
  }
}

export function request(path: string, init?: RequestInit): Promise<Response> {
  const url = path.startsWith('http') ? path : `${API_BASE}${path}`
  return fetch(url, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...sessionHeaders(),
      ...init?.headers,
    },
  }).catch((error: unknown) => {
    if (error instanceof DOMException && error.name === 'AbortError') {
      throw error
    }
    const detail = error instanceof Error ? error.message : '请求未送达'
    throw new Error(`接口请求失败：${detail}`)
  })
}

export async function fetchJson<T>(path: string): Promise<T> {
  const response = await request(path)
  if (!response.ok) {
    throw new Error(`接口返回 ${response.status}，数据未更新`)
  }
  return (await response.json()) as T
}
