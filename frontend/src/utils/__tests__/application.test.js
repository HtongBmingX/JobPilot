/**
 * application.js 纯函数测试
 */
import { describe, it, expect } from 'vitest'
import { parseScore, scoreTier, relativeDate } from '../application.js'

describe('parseScore', () => {
  it('解析百分比', () => {
    expect(parseScore('85%')).toBe(85)
  })

  it('解析带"分"的分数', () => {
    expect(parseScore('85分')).toBe(85)
  })

  it('解析 85/100 格式', () => {
    expect(parseScore('85/100')).toBe(85)
  })

  it('解析纯数字', () => {
    expect(parseScore(85)).toBe(85)
  })

  it('null/undefined 返回 null', () => {
    expect(parseScore(null)).toBe(null)
    expect(parseScore(undefined)).toBe(null)
  })

  it('无法解析的返回 null', () => {
    expect(parseScore('不匹配')).toBe(null)
  })
})

describe('scoreTier', () => {
  it('≥75 是 high', () => {
    expect(scoreTier('85%')).toBe('high')
    expect(scoreTier('75%')).toBe('high')
  })

  it('50-74 是 mid', () => {
    expect(scoreTier('60%')).toBe('mid')
    expect(scoreTier('50%')).toBe('mid')
  })

  it('<50 是 low', () => {
    expect(scoreTier('30%')).toBe('low')
  })

  it('无分数是 none', () => {
    expect(scoreTier(null)).toBe('none')
    expect(scoreTier('')).toBe('none')
  })
})

describe('relativeDate', () => {
  it('今天显示"今天投递"', () => {
    const today = new Date()
    const dateStr = today.toISOString().slice(0, 10)
    expect(relativeDate(dateStr)).toBe('今天投递')
  })

  it('空值返回空字符串', () => {
    expect(relativeDate('')).toBe('')
    expect(relativeDate(null)).toBe('')
  })

  it('无效日期返回原值', () => {
    expect(relativeDate('不是日期')).toBe('不是日期')
  })
})
