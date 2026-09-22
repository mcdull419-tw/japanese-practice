/**
 * data/concepts.json 的查詢層（規格 §5.2）。
 *
 * 這個檔只放「人工定義的文法／助詞概念」，單字概念仍由 concepts.js 的
 * conceptsForVocab 即時生成——約900個單字概念沒有手寫定義的價值。
 *
 * 定義檔刻意不收 skills 欄位（規格 §13 決定 2）：技能一律由 concepts.js 的
 * skillOf() 依 ID 前綴推導，維持單一真相來源。
 *
 * 查不到的概念一律降級而不拋錯——概念定義是輔助資料，缺一筆不該讓整個
 * 題庫載入失敗。label 退回 id 本身（儀表板仍看得出是哪個概念），
 * requires_lesson 退回 1（不擋任何範圍，寧可多出題也不要靜默少出題）。
 */
export function conceptLabel(defs, id) {
  const d = defs && defs[id];
  return d && d.label ? d.label : id;
}

export function requiresLessonOf(defs, id) {
  const d = defs && defs[id];
  return d && typeof d.requires_lesson === 'number' ? d.requires_lesson : 1;
}

export function conceptsByPattern(defs) {
  const map = new Map();
  for (const [id, d] of Object.entries(defs || {})) {
    for (const pid of d.patterns || []) {
      if (!map.has(pid)) map.set(pid, []);
      map.get(pid).push(id);
    }
  }
  return map;
}
