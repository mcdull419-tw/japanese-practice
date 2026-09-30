/**
 * 振假名切詞（規格 §9.3、§13 決定 9）。純函式，回傳 token 陣列，不產生 DOM——
 * `<ruby>` 由 ui/html.js 組裝，core 不得碰 document。
 *
 * 兩條路徑共用同一個 token 形狀：
 *   - annotateWithMarks：課本 sentences[].ruby 的精確標註，優先使用
 *   - annotateWithLexicon：練習Ａ／Ｂ 沒有標註，以詞典最長匹配
 */

/**
 * 標註位置對不上時「跳過該筆」而不是拋錯：ruby 是輔助資訊，語料重抽而位移
 * 不該讓整個題目渲染失敗。真正的把關在 tests/app/test_ruby_lexicon.js 的
 * 漂移測試——那裡對不上就紅燈。
 */
export function annotateWithMarks(text, marks) {
  if (typeof text !== 'string' || text.length === 0) return [];
  const valid = (marks || [])
    .filter((m) => m && typeof m.at === 'number' && typeof m.base === 'string'
      && text.slice(m.at, m.at + m.base.length) === m.base)
    .sort((a, b) => a.at - b.at);

  const out = [];
  let cursor = 0;
  for (const m of valid) {
    if (m.at < cursor) continue; // 重疊標註：保留先出現者
    if (m.at > cursor) out.push({ t: 'text', s: text.slice(cursor, m.at) });
    out.push({ t: 'ruby', base: m.base, kana: m.kana });
    cursor = m.at + m.base.length;
  }
  if (cursor < text.length) out.push({ t: 'text', s: text.slice(cursor) });
  return out;
}
