// 規格 §7：熟悉度模型——近十次答對率 A。
//
// 設計沿革：舊版採 FSRS-lite（S/D 狀態 + retrievability R(t) = (1 + t/(9S))^-1）。
// 已廢止：t≈0 時 R 恆為 1，導致「剛練完不管答對答錯，儀表板都顯示 100%」，使用者
// 拿不到任何有用的訊號。現改為「近十次作答結果的答對率」，不做任何時間衰減。
//
// 事件日誌格式完全不變，舊事件可直接餵進 replay() 重新算出 A（見本檔 tests 的
// 「舊事件可重放」回歸測試）。

export const SRS_CONST = {
  HISTORY_WINDOW: 10, // 規格 §7.1：只看最近幾次作答
};

/** 規格 §7.4：A 只區分 grade >= 2（對）與 grade === 1（錯），四級刻度保留於事件中不動。 */
function isCorrect(grade) {
  return grade >= 2;
}

/**
 * 從 replay() 回傳的 conceptStates 讀出某概念的 A，未考過（不在 map 中）一律為 0。
 * 供 core/ 內外的呼叫端共用，避免「未考過記 0」這個規則分散成好幾份 `?? 0`。
 */
export function conceptA(conceptStates, conceptId) {
  return conceptStates.get(conceptId)?.A ?? 0;
}

/**
 * 事件日誌 → { itemStates, conceptStates }。
 *
 * - itemStates:    Map<itemId, { lastSec, reps }>
 *   供排程器（§8.1）計算 ΔT＝距該題目上次被出的天數。
 * - conceptStates: Map<conceptId, { A, reps }>
 *   A 為該概念最近 min(10, reps) 次作答的答對率；reps 為累計作答次數。
 *   從未考過的概念不會出現在這個 map 裡——呼叫端一律以 conceptA() 取值，
 *   缺席即代表 A=0（規格 §7.1）。
 *
 * 一次作答會更新該題 `covers` 列出的**所有**概念（§7.3、§7.5 的複合題全額歸因），
 * 因此 replay 需要知道每個事件對應題目的 covers 是什麼，故多收一個 itemsById
 * 參數；事件本身的欄位（d/n/i/t/g/r/m）完全不變。
 *
 * nowSec 保留在簽章中只是與呼叫端既有慣例一致，A 的計算完全不使用它——
 * 這正是 §7.2 的重點：A 是「答對率」不是「記憶保留率」，不隨時間打折。
 * 需求 #20（熟悉度隨時間打折）由 §8 排程器的時間項 f(ΔT) 承擔，不由 A 承擔。
 * 不要在這裡把時間折扣加回來：那是本節明確廢止的行為，加回去儀表板又會退回
 * 「剛練完永遠 100%／混淆答錯與太久沒碰」的老問題。
 */
export function replay(events, nowSec, itemsById = new Map()) {
  void nowSec; // 刻意不用——見上方註解

  const sorted = [...events].sort((a, b) => a.t - b.t || (a.n ?? 0) - (b.n ?? 0));

  const itemStates = new Map();
  const queues = new Map(); // conceptId -> { history: boolean[]（先進先出，最多 10 筆）, reps }

  for (const ev of sorted) {
    const prevItem = itemStates.get(ev.i);
    itemStates.set(ev.i, { lastSec: ev.t, reps: (prevItem?.reps ?? 0) + 1 });

    const item = itemsById.get(ev.i);
    const covers = item?.covers || [];
    const correct = isCorrect(ev.g);
    for (const c of covers) {
      const q = queues.get(c) || { history: [], reps: 0 };
      q.history.push(correct);
      if (q.history.length > SRS_CONST.HISTORY_WINDOW) q.history.shift();
      q.reps += 1;
      queues.set(c, q);
    }
  }

  const conceptStates = new Map();
  for (const [c, q] of queues) {
    const hits = q.history.filter(Boolean).length;
    conceptStates.set(c, { A: hits / q.history.length, reps: q.reps });
  }

  return { itemStates, conceptStates };
}
