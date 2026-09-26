import { request } from '@/api/client'

export type ReagentRow = Record<string, string | number | null>

export const ENDPOINT = '/api/reagent'
export const COLUMNS = ['试剂编号', '试剂名称', '规格等级', '生产厂家', '有效期至', '存放位置', '领用人员', '使用状态']
export const ACTIONS = ['领用试剂', '登记用完', '标记过期'] as const

export type ReagentAction = (typeof ACTIONS)[number]

export function actionAvailable(action: ReagentAction, row: ReagentRow): boolean {
  const status = String(row.status ?? '')
  if (action === '领用试剂') return status === '在库'
  if (action === '登记用完') return status === '已领用'
  if (action === '标记过期') return status === '在库' || status === '已领用'
  return false
}

export function rowVersion(row: ReagentRow): number {
  const version = Number(row.version)
  return Number.isInteger(version) && version > 0 ? version : 1
}

export class ActionRejectedError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ActionRejectedError'
  }
}

export class ActionConflictError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ActionConflictError'
  }
}

async function readMessage(response: Response, fallback: string): Promise<string> {
  try {
    const payload = (await response.json()) as { message?: string; detail?: string }
    return payload.message || payload.detail || fallback
  } catch {
    return fallback
  }
}

export async function submitReagentAction(
  action: ReagentAction,
  row: ReagentRow,
  signal?: AbortSignal,
): Promise<ReagentRow> {
  const response = await request(`${ENDPOINT}/${row.id}/actions`, {
    method: 'POST',
    body: JSON.stringify({ action, expectedVersion: rowVersion(row) }),
    signal,
  })

  if (response.status === 403) {
    throw new ActionRejectedError(await readMessage(response, '当前账号无权执行该操作'))
  }
  if (response.status === 409) {
    throw new ActionConflictError(await readMessage(response, '记录已被其他操作更新，请刷新后重试'))
  }
  if (!response.ok) {
    throw new Error(await readMessage(response, '试剂耗材动作未生效，请稍后重试'))
  }

  const payload = (await response.json()) as { ok?: boolean; message?: string; entry?: ReagentRow }
  if (!payload.ok || !payload.entry) {
    throw new ActionRejectedError(payload.message || '试剂耗材动作未生效')
  }
  return payload.entry
}
