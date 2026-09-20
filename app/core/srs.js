export const SRS_CONST = {
  W: 1.0, S_MIN: 0.4, D_MIN: 1.0, D_MAX: 10.0,
  S_INIT: { 1: 0.4, 2: 1.2, 3: 3.2, 4: 9.0 },
  D_INIT: { 1: 7.0, 2: 6.0, 3: 5.0, 4: 4.0 },
  LAPSE_S_FACTOR: 0.4, LAPSE_D_DELTA: 1.0, SUCCESS_D_DELTA: 0.1,
};

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** 規格 §7.2：R(t) = (1 + t/(9S))^-1。純函式，每次讀取時即時計算，不需背景排程。 */
export function retrievability(S, elapsedDays) {
  const s = Math.max(S, SRS_CONST.S_MIN);
  return 1 / (1 + Math.max(0, elapsedDays) / (9 * s));
}

export function initialState(grade) {
  return { S: SRS_CONST.S_INIT[grade], D: SRS_CONST.D_INIT[grade] };
}

export function updateState(state, grade, elapsedDays) {
  const { W, S_MIN, D_MIN, D_MAX, LAPSE_S_FACTOR, LAPSE_D_DELTA, SUCCESS_D_DELTA } = SRS_CONST;
  const S = Math.max(state.S, S_MIN);
  const D = clamp(state.D, D_MIN, D_MAX);
  const R = retrievability(S, elapsedDays);

  if (grade === 1) {
    return { S: Math.max(S_MIN, S * LAPSE_S_FACTOR), D: clamp(D + LAPSE_D_DELTA, D_MIN, D_MAX) };
  }
  // 規格 §7.3：(e^(1-R) - 1) 使「快遺忘時答對」增益最大；
  // S^-0.5 造成邊際遞減；(11 - D) 使難題的間隔不被衝高。
  //
  // 重要：elapsedDays=0 時 R=retrievability(S,0)=1（精確值，見 retrievability 的
  // 定義），此時 (e^(1-R)-1) = (e^0 - 1) = 0，增益精確為 0，S 完全不變。這不是
  // bug，是這個「長期穩定度」公式的必然結果：同一天／同一 session 內再次答對，
  // 尚未提供任何跨越時間的遺忘曲線證據，兩分鐘後記得不代表兩天後也記得，因此
  // 不該給穩定度增益（真實 FSRS 對同日重複複習另有一套「短期穩定度」模型，
  // 不在這個 lite 版的範圍內）。
  //
  // 這會直接影響規格 §8 的 lapse re-drill：答錯的題目在 3~5 題後於同一 session
  // 重新插入，此時 elapsedDays≈0，即使那次重答也答對，S 也不會增加——這是正確
  // 行為，請勿「修好」它（例如強加一個非零的最低增益）。真正的鞏固要等到下一次
  // 跨天複習、R 已顯著低於 1 時才會反映在 S 的成長上。
  const gain = Math.exp(W) * (11 - D) * Math.pow(S, -0.5) * (Math.exp(1 - R) - 1);
  return {
    S: Math.max(S_MIN, S * (1 + gain)),
    D: clamp(D - SUCCESS_D_DELTA * (grade - 3), D_MIN, D_MAX),
  };
}

const SEC_PER_DAY = 86400;

/** 事件日誌 → 每題的目前狀態。事件不可變，重放即可，故演算法調整後可重算歷史。 */
export function replay(events, nowSec) {
  const sorted = [...events].sort((a, b) => a.t - b.t || (a.n ?? 0) - (b.n ?? 0));
  const out = new Map();
  for (const ev of sorted) {
    const prev = out.get(ev.i);
    if (!prev) {
      const { S, D } = initialState(ev.g);
      out.set(ev.i, { S, D, lastSec: ev.t, reps: 1, lapses: ev.g === 1 ? 1 : 0 });
      continue;
    }
    const elapsed = (ev.t - prev.lastSec) / SEC_PER_DAY;
    const next = updateState(prev, ev.g, elapsed);
    out.set(ev.i, {
      ...next, lastSec: ev.t, reps: prev.reps + 1,
      lapses: prev.lapses + (ev.g === 1 ? 1 : 0),
    });
  }
  for (const [id, st] of out) {
    out.set(id, { ...st, R: retrievability(st.S, (nowSec - st.lastSec) / SEC_PER_DAY) });
  }
  return out;
}
