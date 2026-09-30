// HTML 字串組裝。純字串處理（不碰 document），供 ui/ 與 engines/ 共用。
const ENTITIES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

export function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ENTITIES[c]);
}

/**
 * 規格 §9.3：假名置於漢字上方（ruby-position: over，瀏覽器預設值）。
 *
 * hideRt 為真時**不產生 rt 元素**，而不是以 CSS 隱藏——考讀音的題型若把答案
 * 留在 DOM 裡，長按選取或檢視原始碼就看得到，等於沒藏。
 */
export function rubyHtml(tokens, { hideRt = false } = {}) {
  return (tokens || []).map((t) => {
    if (t.t === 'ruby') {
      const base = escapeHtml(t.base);
      return hideRt ? base : `<ruby>${base}<rt>${escapeHtml(t.kana)}</rt></ruby>`;
    }
    return escapeHtml(t.s).replace(/\n/g, '<br>');
  }).join('');
}
