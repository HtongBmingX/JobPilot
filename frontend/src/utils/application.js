/**
 * application.js — 投递记录展示相关的纯函数工具
 *
 * 为什么抽出来？匹配分解析、色阶判断、相对日期这几个逻辑
 * JobCard（卡片）和 ApplicationDetailModal（详情弹窗）都要用，
 * 抽成纯函数方便复用和单独测试。
 */

/** 从 "85%" / "85分" / "85/100" / 85 等格式里提取数字 */
export function parseScore(score) {
  if (score == null) return null
  const m = String(score).match(/(\d+(?:\.\d+)?)/)
  if (!m) return null
  const n = Number(m[1])
  return Number.isFinite(n) ? n : null
}

/**
 * 匹配分色阶：high(≥75) / mid(50-74) / low(<50) / none(无分数)
 * 这是卡片的视觉锚点——扫一眼就知道哪些投递值得优先跟进。
 */
export function scoreTier(score) {
  const n = parseScore(score)
  if (n == null) return 'none'
  if (n >= 75) return 'high'
  if (n >= 50) return 'mid'
  return 'low'
}

/** 把投递日期转成相对表达："今天投递" / "昨天投递" / "3 天前投递" / 原值 */
export function relativeDate(dateStr) {
  if (!dateStr) return ''
  // 只取 "YYYY-MM-DD" 部分，避免时区偏移把日期算错一天
  const dateOnly = String(dateStr).slice(0, 10)
  const parts = dateOnly.split('-').map(Number)
  if (parts.length !== 3 || parts.some(Number.isNaN)) return String(dateStr)

  const [y, m, d] = parts
  const thatDay = new Date(y, m - 1, d)
  const now = new Date()
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
  const diff = Math.round((today - thatDay) / 86400000)

  if (diff === 0) return '今天投递'
  if (diff === 1) return '昨天投递'
  if (diff > 1 && diff < 30) return `${diff} 天前投递`
  // 未来日期或超过 30 天，直接显示原值
  return String(dateStr)
}
