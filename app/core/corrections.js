/**
 * 題庫更正迴路（使用者需求，2026-09-30）。
 *
 * 練習Ｂ 的 210 句答案是人工書寫的，沒有結構性的自動把關可用（規格 §13
 * 決定 11）。因此留一條「發現可疑 → 匯出查證 → 回寫更正」的路：
 *
 *   1. 練習時按「這題怪怪的」→ 寫入 m='flag' 事件（core/store.js）
 *   2. 設定區匯出待確認清單 → exportFlagged()，拿去對照課本或別的工具
 *   3. 查證後把更正寫進 data/corrections.json → applyCorrections() 套用
 *
 * 更正檔與使用者資料分開存放（規格 §9.2.1）：corrections.json 是隨網站部署的
 * 靜態檔，記的是「題庫本身錯了」；使用者的 flag 與自訂答案是個人資料，存在
 * 事件日誌裡。兩者在載入時合併，更正檔先套、使用者層後套。
 */

/**
 * 把被標記的題目整理成可讀的清單。帶上題幹與正解，才有辦法離開這個網站
 * 去查證——只給 id 的話，拿到別的工具上無從判斷對錯。
 */
export function exportFlagged(flagged, itemsById) {
  const out = [];
  for (const [itemId, flaggedAt] of flagged) {
    const it = itemsById.get(itemId);
    out.push({
      id: itemId,
      flagged_at: new Date(flaggedAt * 1000).toISOString(),
      // 題目可能因為課次範圍或題型設定而不在本輪題庫中，此時只能給 id。
      prompt: it ? it.prompt.text : null,
      answer: it ? it.answer : null,
      source_ref: it ? it.source_ref : null,
      covers: it ? it.covers : null,
    });
  }
  return out.sort((a, b) => (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));
}

/**
 * 套用 data/corrections.json。以 item id 為鍵，可覆蓋 answer、alternatives
 * 與 prompt.text；未列出的欄位原樣保留。
 *
 * 找不到對應題目的更正**不在這裡報錯**——課次範圍縮小時，本輪題庫本來就不會
 * 有那道題。孤兒更正由 tests/app/test_corrections.js 在全量題庫上檢查。
 */
export function applyCorrections(items, corrections) {
  if (!corrections || Object.keys(corrections).length === 0) return items;
  return items.map((it) => {
    const fix = corrections[it.id];
    if (!fix) return it;
    const next = { ...it };
    if (fix.answer != null) next.answer = fix.answer;
    if (fix.alternatives != null) {
      next.alternatives = [...new Set([...(it.alternatives || []), ...fix.alternatives])];
    }
    if (fix.prompt != null) next.prompt = { ...it.prompt, text: fix.prompt };
    return next;
  });
}
