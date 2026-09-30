/**
 * 事件日誌儲存（規格 §10.1）。
 *
 * 儲存的是事件而非分數：
 *   1. 演算法調整後可重放歷史，重新算出熟悉度；
 *   2. 多裝置合併只是取事件聯集，永不衝突；
 *   3. 支援後續的學習分析。
 *
 * 事件的全域唯一鍵是 (d, n)——裝置 id 與該裝置的單調遞增序號，不是 (i, t)：
 * 時戳只到秒會碰撞，且無法區分「同一題連續作答兩次」與「重複匯入同一筆事件」。
 */

/**
 * 規格 §10.1。`alt` 為選用參數——只有「我這樣寫也對」補記的那一筆會帶，
 * 帶了才會多出 `a` 欄位；一般作答事件的形狀與舊版完全相同。
 */
export function makeEvent(deviceId, seq, itemId, grade, rtMs, mode, nowSec, alt) {
  const ev = { d: deviceId, n: seq, i: itemId, t: nowSec, g: grade, r: rtMs, m: mode };
  if (alt) ev.a = alt;
  return ev;
}

/**
 * 「這題怪怪的」標記。與作答事件同一個日誌（因此匯出、同步都自動帶著走），
 * 以 m='flag' 區分——重放時略過，不影響任何熟悉度計算（見 srs.js 的 replay）。
 *
 * g 與 r 補 0 只是為了讓事件形狀一致；這兩個欄位對標記沒有意義。
 */
export function makeFlagEvent(deviceId, seq, itemId, nowSec) {
  return { d: deviceId, n: seq, i: itemId, t: nowSec, g: 0, r: 0, m: 'flag' };
}

/** 從事件日誌重建「被標記過的題目 → 最後一次標記的時戳」。 */
export function flaggedFrom(events) {
  const out = new Map();
  for (const e of events) {
    if (e.m !== 'flag') continue;
    const prev = out.get(e.i);
    if (prev == null || e.t > prev) out.set(e.i, e.t);
  }
  return out;
}

/**
 * 規格 §9.2.1／§10.1：從事件日誌重建每題的自訂 alternatives。
 *
 * 使用者認可的寫法是事件的一部分（欄位 `a`），不存 localStorage——localStorage
 * 不在 allEvents() 的輸出裡，會讓 exportJSON() 漏掉這些寫法，Phase 3 的同步也
 * 完全帶不過去（在 Mac 上認可的寫法，手機不會知道）。
 *
 * 舊事件沒有 `a` 欄位，直接略過即可。
 */
export function userAlternativesFrom(events) {
  const out = new Map();
  for (const e of events) {
    if (!e.a) continue;
    const list = out.get(e.i) || [];
    if (!list.includes(e.a)) list.push(e.a);
    out.set(e.i, list);
  }
  return out;
}

/** 以 (d,n) 去重、依時間排序（同秒以 n 為次序 tie-break，維持穩定順序）。 */
export function mergeEvents(a, b) {
  const seen = new Map();
  for (const e of [...a, ...b]) seen.set(`${e.d}#${e.n}`, e);
  return [...seen.values()].sort((x, y) => x.t - y.t || x.n - y.n);
}

export class MemoryStore {
  constructor() {
    this._events = [];
  }
  async appendEvents(evs) {
    this._events = mergeEvents(this._events, evs);
  }
  async allEvents() {
    return [...this._events];
  }
  async exportJSON() {
    return JSON.stringify({ version: 1, events: this._events });
  }
  async importJSON(s) {
    const parsed = JSON.parse(s);
    await this.appendEvents(parsed.events || []);
  }
}

const DB_NAME = 'japanese-practice';
const STORE = 'events';

/**
 * IndexedDB 實作。無法在 Node 測試環境驗證（沒有 IndexedDB），由 Task 14
 * 的手動瀏覽器驗收涵蓋。為了不讓 app/core 碰全域 DOM，indexedDB 的 factory
 * 一律由呼叫端注入（openStore 的參數），本檔絕不直接引用全域 `indexedDB`。
 */
export class LocalStore {
  constructor(db) {
    this._db = db;
  }

  static async open(idbFactory) {
    const db = await new Promise((resolve, reject) => {
      const req = idbFactory.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        // 主鍵為 [d, n]，唯一性直接由 IndexedDB 保證，不需應用層去重。
        req.result.createObjectStore(STORE, { keyPath: ['d', 'n'] });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return new LocalStore(db);
  }

  _tx(mode) {
    return this._db.transaction(STORE, mode).objectStore(STORE);
  }

  async appendEvents(evs) {
    await new Promise((resolve, reject) => {
      const tx = this._db.transaction(STORE, 'readwrite');
      const os = tx.objectStore(STORE);
      for (const e of evs) os.put(e); // put 而非 add：重複 (d,n) 覆寫而非拋錯
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  async allEvents() {
    const rows = await new Promise((resolve, reject) => {
      const req = this._tx('readonly').getAll();
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return rows.sort((a, b) => a.t - b.t || a.n - b.n);
  }

  async exportJSON() {
    return JSON.stringify({ version: 1, events: await this.allEvents() });
  }
  async importJSON(s) {
    await this.appendEvents(JSON.parse(s).events || []);
  }
}

/** 有 IndexedDB factory 就用 LocalStore（持久化），否則退回 MemoryStore。 */
export async function openStore(indexedDBFactory) {
  if (indexedDBFactory) {
    try {
      return await LocalStore.open(indexedDBFactory);
    } catch {
      // 私密視窗或封鎖站台資料時 IndexedDB 可能無法使用，退回記憶體儲存。
    }
  }
  return new MemoryStore();
}
