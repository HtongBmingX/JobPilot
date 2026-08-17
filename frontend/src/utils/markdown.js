import { marked } from 'marked'

/**
 * 将 Markdown 文本渲染为安全的 HTML 字符串。
 *
 * 为什么需要 sanitize？marked 不防止 XSS。如果后端返回的 Markdown
 * 中包含 <script> 或 onclick="..."，直接 v-html 会执行恶意代码。
 * 这里的 stripDangerousTags 是最小化的防护——只移除危险标签和属性，
 * 不依赖额外的库（如 DOMPurify）。
 *
 * 局限：这是一道「够用」的防线而非完整的安全方案。如果你计划让
 * 项目上线且用户可以互相看到对方的输出，请引入 DOMPurify。
 */
export function renderMarkdown(raw) {
  if (!raw) return ''

  // marked.parse 将 Markdown 转为 HTML
  const html = marked.parse(raw, {
    breaks: true,       // 单换行也转 <br>，更符合中文输入习惯
    gfm: true,          // GitHub Flavored Markdown（表格、任务列表等）
  })

  return sanitize(html)
}

/**
 * 移除危险的 HTML 标签和事件处理属性。
 * 只保留安全的格式化标签。
 */
function sanitize(html) {
  // 移除 <script>、<iframe>、<object>、<embed>、<svg>、<math>、<form>、<meta>、<link> 等危险标签
  const dangerousTags = [
    'script', 'iframe', 'object', 'embed', 'svg', 'math',
    'form', 'meta', 'link', 'style', 'base', 'frame', 'frameset',
  ]
  for (const tag of dangerousTags) {
    const re = new RegExp(`<${tag}\\b[^>]*(?:[\\s\\S]*?</${tag}>)?`, 'gi')
    html = html.replace(re, '')
  }

  // 移除 on* 事件属性（onclick, onerror, onload 等）
  html = html.replace(/\s+on\w+\s*=\s*"[^"]*"/gi, '')
  html = html.replace(/\s+on\w+\s*=\s*'[^']*'/gi, '')
  html = html.replace(/\s+on\w+\s*=\s*[^\s>]+/gi, '')

  // 移除 javascript: 协议链接（href / src / xlink:href 等）
  html = html.replace(/(href|src|xlink:href)\s*=\s*"javascript:[^"]*"/gi, '$1="#"')
  html = html.replace(/(href|src|xlink:href)\s*=\s*'javascript:[^']*'/gi, "$1='#'")
  html = html.replace(/(href|src|xlink:href)\s*=\s*javascript:[^\s>]+/gi, '$1="#"')

  return html
}
