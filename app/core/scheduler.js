// 規格 §8：排程器。加權隨機抽樣（不是排序取前 N），使熟悉度低的題目／概念更常被抽到，
// 但每次練習仍有變化，避免使用者背下固定順序。
//
// priority(item) = (1 - R_item) · max over c∈covers (1 - R_c) · freshness(item)
// 權重 = priority^ALPHA，依權重隨機抽樣（見 pickItems）。

const ALPHA = 2;              // 權重指數：priority^ALPHA
const UNSEEN_R = 0;           // 未練過視為完全生疏
const NEW_ITEM_RATIO = 0.3;   // 規格 §8：新題比例上限 30%／session

export function buildConceptStates(itemStates, items) {
  const acc = new Map();
  for (const it of items) {
    const st = itemStates.get(it.id);
    if (!st) continue;
    const w = Math.log(1 + (st.reps ?? 0)) || 0.0001;
    for (const c of it.covers || []) {
      const cur = acc.get(c) || { sum: 0, w: 0, reps: 0 };
      cur.sum += st.R * w; cur.w += w; cur.reps += st.reps ?? 0;
      acc.set(c, cur);
    }
  }
  const out = new Map();
  for (const [c, v] of acc) out.set(c, { R: v.w > 0 ? v.sum / v.w : UNSEEN_R, reps: v.reps });
  return out;
}

/** 規格 §8：(1-R_item) × max(1-R_concept) × freshness */
export function priority(item, itemStates, conceptStates, seenThisSession = new Set()) {
  const itemR = itemStates.get(item.id)?.R ?? UNSEEN_R;
  const covers = item.covers || [];
  // max over c∈covers (1 - R_c)：初始值須為 0（(1-R_c) 的值域下界），
  // 若初始為 1，max 恆等於 1，會讓概念熟悉度完全無法影響優先度（跨題型傳導失效）。
  // 只有在題目完全沒有 covers（不應發生，但防禦性處理）時才退回 1，避免優先度被歸零。
  let conceptGap = covers.length === 0 ? 1 : 0;
  for (const c of covers) {
    const r = conceptStates.get(c)?.R ?? UNSEEN_R;
    conceptGap = Math.max(conceptGap, 1 - r);
  }
  const freshness = seenThisSession.has(item.id) ? 0.05 : 1;
  return Math.max(1e-6, (1 - itemR)) * conceptGap * freshness;
}

function weightedPick(candidates, itemStates, conceptStates, seen, rng) {
  const weights = candidates.map((it) =>
    Math.pow(priority(it, itemStates, conceptStates, seen), ALPHA));
  const total = weights.reduce((a, b) => a + b, 0);
  let target = rng() * total;
  let idx = candidates.length - 1;
  for (let k = 0; k < candidates.length; k++) {
    target -= weights[k];
    if (target <= 0) { idx = k; break; }
  }
  return idx;
}

export function pickItems(items, itemStates, conceptStates, count, rng = Math.random) {
  const pool = [...items];
  const picked = [];
  const seen = new Set();
  const newCap = Math.floor(count * NEW_ITEM_RATIO);
  let newPicked = 0;
  const isNew = (it) => !itemStates.get(it.id);

  while (picked.length < count && pool.length > 0) {
    // 新題比例上限（規格 §8）：若已達上限，且池中仍有練過的舊題可選，
    // 這一輪就只從舊題中抽，避免一次灌入過多生題。若舊題已抽完，仍讓新題補滿名額，
    // 優先確保「回傳全部，不無限迴圈」。
    let candidates = pool;
    if (newPicked >= newCap) {
      const oldOnes = pool.filter((it) => !isNew(it));
      if (oldOnes.length > 0) candidates = oldOnes;
    }

    const idx = weightedPick(candidates, itemStates, conceptStates, seen, rng);
    const chosen = candidates[idx];
    pool.splice(pool.indexOf(chosen), 1);
    picked.push(chosen);
    seen.add(chosen.id);
    if (isNew(chosen)) newPicked++;
  }
  return picked;
}
