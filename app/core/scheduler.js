// 規格 §8：排程器。出題權重 W 愈高愈該出，桶內加權隨機抽樣（不是排序取前 N——
// 純排序會讓每次練習都是同幾題，使用者會背下順序而非內容）。
//
// W(item) = (1 - A_item) + f(ΔT_item)
// A_item  = min over c ∈ item.covers 之 A_c        最弱環節
// f(ΔT)   = ΔT / (ΔT + K_DAYS)                     ΔT = 距該題目上次被出的天數
//
// 兩項各自落在 0~1，故 W ∈ [0, 2]。A_item 取 min 而非平均，是為了讓「這題考到
// 的任何一個弱概念」都足以把它拉上來（一道變化題同時考 r:te:I 與 w:送:group，
// 只要其中一個不熟就該練）。

import { conceptA } from './srs.js';

export const SCHED_CONST = {
  K_DAYS: 7,              // f(ΔT) 的刻度（規格 §8.1），可調
  BUCKET_HIGH: 1.0,        // W >= 此值 → 高桶
  BUCKET_MID: 0.4,         // BUCKET_MID <= W < BUCKET_HIGH → 中桶；W < BUCKET_MID → 低桶
  NEW_ITEM_RATIO: 0.3,     // 新題比例上限／session（規格 §8.2）
  SESSION_SEEN_DECAY: 0.05, // 本 session 已出現過的題目，權重乘上此值（規格 §8.2）
};

const SEC_PER_DAY = 86400;
const EPSILON = 1e-6; // 避免權重恰為 0 時整批候選權重和為 0

/** 規格 §8.1：f(ΔT) = ΔT / (ΔT + k)。從未出過（deltaTDays == null）時 f = 0。 */
export function timeFactor(deltaTDays) {
  if (deltaTDays == null || deltaTDays <= 0) return 0;
  return deltaTDays / (deltaTDays + SCHED_CONST.K_DAYS);
}

/** 規格 §8.1：W(item) = (1 - A_item) + f(ΔT_item)。A_item 取 covers 中最低者。 */
export function priority(item, itemStates, conceptStates, nowSec) {
  const covers = item.covers || [];
  // min 的初始值須為 1（(1-A) 的值域上界對應 A 下界 0），若題目完全沒有 covers
  // （不應發生，但防禦性處理）就當作最不熟，避免優先度被誤判為 0 而永遠不出現。
  let aItem = covers.length === 0 ? 0 : 1;
  for (const c of covers) {
    aItem = Math.min(aItem, conceptA(conceptStates, c));
  }

  const itemState = itemStates.get(item.id);
  const deltaTDays = itemState ? Math.max(0, (nowSec - itemState.lastSec) / SEC_PER_DAY) : null;
  const f = timeFactor(deltaTDays);

  return (1 - aItem) + f;
}

/** 規格 §8.2：高＝W≥1.0、中＝0.4≤W<1.0、低＝W<0.4。 */
export function bucketOf(w) {
  if (w >= SCHED_CONST.BUCKET_HIGH) return 'high';
  if (w >= SCHED_CONST.BUCKET_MID) return 'mid';
  return 'low';
}

function weightedPick(candidates, seen, rng) {
  const weights = candidates.map((c) => {
    const decay = seen.has(c.item.id) ? SCHED_CONST.SESSION_SEEN_DECAY : 1;
    return Math.max(EPSILON, c.w) * decay;
  });
  const total = weights.reduce((a, b) => a + b, 0);
  let target = rng() * total;
  let idx = candidates.length - 1;
  for (let k = 0; k < candidates.length; k++) {
    target -= weights[k];
    if (target <= 0) { idx = k; break; }
  }
  return idx;
}

/**
 * 規格 §8.2：分桶與抽樣。
 * - 只從「高」與「中」兩桶出題，桶內以 W 為權重隨機抽樣。
 * - 若高＋中的題數不足本次所需，才把「低」桶一併納入。
 * - 本 session 已出現過的題目（seenThisSession，跨呼叫維護），W 乘上
 *   SESSION_SEEN_DECAY 強力衰減，避免同一輪重複。
 * - 新題比例上限 NEW_ITEM_RATIO，避免一次灌入過多從未考過的題目。
 */
export function pickItems(items, itemStates, conceptStates, count, nowSec, rng = Math.random, seenThisSession = new Set()) {
  const withW = items.map((item) => ({
    item,
    w: priority(item, itemStates, conceptStates, nowSec),
  }));
  const highMid = withW.filter((x) => bucketOf(x.w) !== 'low');
  // W 在整個 pickItems 呼叫期間不變（session-seen 衰減只影響抽樣權重，不影響
  // 桶籍判定），因此桶籍只需算一次，不必在抽樣迴圈中每輪重算。
  const basePool = highMid.length >= count ? highMid : withW;

  let pool = [...basePool];
  const picked = [];
  const seen = new Set(seenThisSession);
  const newCap = Math.floor(count * SCHED_CONST.NEW_ITEM_RATIO);
  let newPicked = 0;
  const isNew = (it) => !itemStates.get(it.id);

  while (picked.length < count && pool.length > 0) {
    // 新題比例上限：若已達上限，且池中仍有練過的舊題可選，這一輪就只從舊題中抽。
    // 若舊題已抽完，仍讓新題補滿名額，優先確保「回傳全部，不無限迴圈」。
    let candidates = pool;
    if (newPicked >= newCap) {
      const oldOnes = pool.filter((c) => !isNew(c.item));
      if (oldOnes.length > 0) candidates = oldOnes;
    }

    const idx = weightedPick(candidates, seen, rng);
    const chosen = candidates[idx];
    pool.splice(pool.findIndex((c) => c.item.id === chosen.item.id), 1);
    picked.push(chosen.item);
    seen.add(chosen.item.id);
    if (isNew(chosen.item)) newPicked++;
  }
  return picked;
}
