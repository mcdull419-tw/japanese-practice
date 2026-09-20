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
