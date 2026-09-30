import { test } from 'node:test';
import assert from 'node:assert/strict';
import { replay, conceptA, SRS_CONST } from '../../app/core/srs.js';

const DAY = 86400;

function mkEvents(itemId, grades, startT = 0) {
  return grades.map((g, i) => ({ d: 'dev', n: i, i: itemId, t: startT + i * DAY, g, r: 1000, m: 'text' }));
}

test('考 5 次對 3 次 → A = 0.6', () => {
  const items = new Map([['it1', { id: 'it1', covers: ['w:a'] }]]);
  const events = mkEvents('it1', [3, 1, 3, 1, 3]); // 對錯對錯對
  const { conceptStates } = replay(events, 100 * DAY, items);
  assert.equal(conceptA(conceptStates, 'w:a'), 0.6);
});

test('考 20 次 → 只看最近 10 次（前 10 次全錯、後 10 次全對 → A = 1.0）', () => {
  const items = new Map([['it1', { id: 'it1', covers: ['w:a'] }]]);
  const grades = [...Array(10).fill(1), ...Array(10).fill(3)];
  const events = mkEvents('it1', grades);
  const { conceptStates } = replay(events, 100 * DAY, items);
  assert.equal(conceptA(conceptStates, 'w:a'), 1.0);
  assert.equal(conceptStates.get('w:a').reps, 20);
});

test('從未考過 → A = 0', () => {
  const { conceptStates } = replay([], 0, new Map());
  assert.equal(conceptA(conceptStates, 'w:never-seen'), 0);
});

test('grade=1 記為錯，grade 2/3/4 都記為對', () => {
  const items = new Map([['it1', { id: 'it1', covers: ['w:a'] }]]);
  const events = mkEvents('it1', [1, 2, 3, 4]);
  const { conceptStates } = replay(events, 100 * DAY, items);
  // 1 錯、2/3/4 對 → 3/4 = 0.75
  assert.equal(conceptA(conceptStates, 'w:a'), 0.75);
});

test('A 不隨時間衰減——同一批事件，nowSec 相差一年，A 完全相同（回歸測試）', () => {
  const items = new Map([['it1', { id: 'it1', covers: ['w:a'] }]]);
  const events = mkEvents('it1', [3, 1, 3, 1, 3]);
  const a1 = replay(events, 100 * DAY, items).conceptStates.get('w:a').A;
  const a2 = replay(events, 100 * DAY + 365 * DAY, items).conceptStates.get('w:a').A;
  assert.equal(a1, a2);
});

test('一次作答更新該題 covers 的所有概念（複合題全額歸因，§7.5）', () => {
  const items = new Map([['it1', { id: 'it1', covers: ['g:x', 'p:ni'] }]]);
  const events = mkEvents('it1', [1]);
  const { conceptStates } = replay(events, DAY, items);
  assert.equal(conceptA(conceptStates, 'g:x'), 0);
  assert.equal(conceptA(conceptStates, 'p:ni'), 0);
});

test('replay 與事件輸入順序無關（會先排序）', () => {
  const items = new Map([['it1', { id: 'it1', covers: ['w:a'] }]]);
  const events = mkEvents('it1', [3, 1, 3]);
  const m1 = replay(events, 10 * DAY, items);
  const m2 = replay([...events].reverse(), 10 * DAY, items);
  assert.deepEqual(m1.conceptStates.get('w:a'), m2.conceptStates.get('w:a'));
  assert.deepEqual(m1.itemStates.get('it1'), m2.itemStates.get('it1'));
});

test('itemStates 記錄每個題目的 lastSec 與 reps', () => {
  const items = new Map([['it1', { id: 'it1', covers: ['w:a'] }]]);
  const events = mkEvents('it1', [3, 1, 3]);
  const { itemStates } = replay(events, 10 * DAY, items);
  assert.equal(itemStates.get('it1').reps, 3);
  assert.equal(itemStates.get('it1').lastSec, 2 * DAY);
});

test('舊事件（{d,n,i,t,g,r,m} 格式）可直接餵進新的 replay，不拋錯且算出合理的 A', () => {
  // 模擬使用者 IndexedDB 裡既有的真實作答紀錄：舊格式事件，欄位與型別完全比照
  // 規格 §10.1，換模型後必須還能讀（規格 §7 開頭：「事件日誌格式未變，舊事件
  // 可直接重放」）。
  const legacyEvents = [
    { d: 'dev-abc123', n: 0, i: 'w:kaerimasu', t: 1757000000, g: 3, r: 1800, m: 'text' },
    { d: 'dev-abc123', n: 1, i: 'w:kaerimasu', t: 1757003600, g: 1, r: 4200, m: 'text' },
    { d: 'dev-abc123', n: 2, i: 'w:kaerimasu', t: 1757090000, g: 4, r: 900, m: 'audio' },
    { d: 'dev-abc123', n: 3, i: 'conj:kaerimasu:masu→te', t: 1757176400, g: 2, r: 3000, m: 'text' },
  ];
  const itemsById = new Map([
    ['w:kaerimasu', { id: 'w:kaerimasu', covers: ['w:帰ります'] }],
    ['conj:kaerimasu:masu→te', { id: 'conj:kaerimasu:masu→te', covers: ['r:te:groupI', 'w:帰ります:group'] }],
  ]);
  const nowSec = 1757176400 + 365 * DAY;

  assert.doesNotThrow(() => replay(legacyEvents, nowSec, itemsById));

  const { conceptStates, itemStates } = replay(legacyEvents, nowSec, itemsById);
  // w:帰ります 出現三次：對、錯、對 → 2/3
  assert.equal(conceptA(conceptStates, 'w:帰ります'), 2 / 3);
  // r:te:groupI 與 w:帰ります:group 各出現一次，grade=2（對）→ A=1
  assert.equal(conceptA(conceptStates, 'r:te:groupI'), 1);
  assert.equal(conceptA(conceptStates, 'w:帰ります:group'), 1);
  assert.equal(itemStates.get('w:kaerimasu').reps, 3);
});

test('SRS_CONST.HISTORY_WINDOW 為具名常數，非散落的魔術數字', () => {
  assert.equal(SRS_CONST.HISTORY_WINDOW, 10);
});

// ── 標記事件不得影響熟悉度與排程 ─────────────────────────────
import { makeFlagEvent } from '../../app/core/store.js';

test('重放略過 flag 事件：不算複習、不動 A、不更新 lastSec', () => {
  const items = new Map([['x', { id: 'x', covers: ['w:A'] }]]);
  const answered = [{ d: 'd', n: 1, i: 'x', t: 100, g: 3, r: 10, m: 'text' }];
  const withFlag = [...answered, makeFlagEvent('d', 2, 'x', 999)];

  const a = replay(answered, 1000, items);
  const b = replay(withFlag, 1000, items);

  assert.equal(b.itemStates.get('x').reps, a.itemStates.get('x').reps,
    'flag 不該被算成一次複習');
  assert.equal(b.itemStates.get('x').lastSec, 100,
    'flag 不該更新 lastSec——否則標記題目反而讓它更少出現');
  assert.equal(b.conceptStates.get('w:A').A, a.conceptStates.get('w:A').A);
});
