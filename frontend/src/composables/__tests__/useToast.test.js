/**
 * useToast 测试（模块级单例，注意状态在测试间共享）
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { useToast } from '../useToast.js'

// 每个测试前清空 toasts，避免单例状态串扰
let toast
beforeEach(() => {
  toast = useToast()
  toast.toasts.splice(0, toast.toasts.length)
})

describe('useToast', () => {
  it('success 添加 success 类型的 toast', () => {
    toast.success('保存成功')
    expect(toast.toasts.length).toBe(1)
    expect(toast.toasts[0].type).toBe('success')
    expect(toast.toasts[0].message).toBe('保存成功')
  })

  it('error 添加 error 类型', () => {
    toast.error('出错了')
    expect(toast.toasts[0].type).toBe('error')
  })

  it('info 添加 info 类型', () => {
    toast.info('提示')
    expect(toast.toasts[0].type).toBe('info')
  })

  it('dismiss 移除指定 toast', () => {
    const id = toast.success('待删除')
    expect(toast.toasts.length).toBe(1)
    toast.dismiss(id)
    expect(toast.toasts.length).toBe(0)
  })

  it('dismiss 不存在的 id 不报错', () => {
    toast.dismiss(99999)
    expect(toast.toasts.length).toBe(0)
  })
})
