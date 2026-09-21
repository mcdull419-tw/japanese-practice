import { test } from 'node:test';
import assert from 'node:assert/strict';
import { priority, pickItems, timeFactor, bucketOf, SCHED_CONST } from '../../app/core/scheduler.js';

const DAY = 86400;
const near = (a, b, tol = 0.01) => assert.ok(Math.abs(a - b) < tol, `${a} vs ${b}`);

const mkItem = (id, covers) => ({ id, covers, requires_lesson: 1, engine: 'recall' });

test('f(ΔT) 的刻度（k=7，規格 §8.1）', () => {
  near(timeFactor(1), 0.13);
  near(timeFactor(3), 0.30);
  near(timeFactor(7), 0.50);
  near(timeFactor(14), 0.67);
  near(timeFactor(30), 0.81);
});

test('從未出過（ΔT 不存在）f = 0', () => {
  assert.equal(timeFactor(null), 0);
});

test('規格 §8.1 代表情境表：六列 W 值與分桶', () => {
  const now = 1000 * DAY;
  const it = mkItem('i1', ['w:x']);

  // 不熟又很久沒考：A=0.0，ΔT=30 天 → W=1.81，高
  {
    const cs = new Map([['w:x', { A: 0.0, reps: 5 }]]);
    const st = new Map([['i1', { lastSec: now - 30 * DAY, reps: 5 }]]);
    const w = priority(it, st, cs, now);
    near(w, 1.81);
    assert.equal(bucketOf(w), 'high');
  }
  // 從未考過：A=0.0，ΔT=— → W=1.00，高
  {
    const cs = new Map();
    const st = new Map();
    const w = priority(it, st, cs, now);
    near(w, 1.00);
    assert.equal(bucketOf(w), 'high');
  }
  // 不熟但剛考過：A=0.0，ΔT=今天 → W=1.00，高
  {
    const cs = new Map([['w:x', { A: 0.0, reps: 3 }]]);
    const st = new Map([['i1', { lastSec: now, reps: 3 }]]);
    const w = priority(it, st, cs, now);
    near(w, 1.00);
    assert.equal(bucketOf(w), 'high');
  }
  // 半生不熟、一週沒碰：A=0.5，ΔT=7 天 → W=1.00，高
  {
    const cs = new Map([['w:x', { A: 0.5, reps: 4 }]]);
    const st = new Map([['i1', { lastSec: now - 7 * DAY, reps: 4 }]]);
    const w = priority(it, st, cs, now);
    near(w, 1.00);
    assert.equal(bucketOf(w), 'high');
  }
  // 熟但很久沒考：A=1.0，ΔT=30 天 → W=0.81，中
  {
    const cs = new Map([['w:x', { A: 1.0, reps: 10 }]]);
    const st = new Map([['i1', { lastSec: now - 30 * DAY, reps: 10 }]]);
    const w = priority(it, st, cs, now);
    near(w, 0.81);
    assert.equal(bucketOf(w), 'mid');
  }
  // 熟又剛考過：A=1.0，ΔT=今天 → W=0.00，低
  {
    const cs = new Map([['w:x', { A: 1.0, reps: 10 }]]);
    const st = new Map([['i1', { lastSec: now, reps: 10 }]]);
    const w = priority(it, st, cs, now);
    near(w, 0.00);
    assert.equal(bucketOf(w), 'low');
  }
});

test('A_item 取 covers 中最低者（最弱環節）', () => {
  const it = mkItem('i1', ['r:te:groupI', 'w:x:group']);
  const now = 100 * DAY;
  const cs = new Map([
    ['r:te:groupI', { A: 0.9, reps: 20 }],
    ['w:x:group', { A: 0.1, reps: 2 }],
  ]);
  const w = priority(it, new Map(), cs, now);
  near(w, (1 - 0.1) + 0); // 從未出過此題 → f=0；A_item 取 min(0.9, 0.1)=0.1
});

test('只從高＋中兩桶出題', () => {
  const now = 100 * DAY;
  // low：A=1.0 剛考過 → W=0
  const lowItem = mkItem('low1', ['w:low']);
  // high：從未考過 → W=1.0
  const highItem = mkItem('high1', ['w:high']);
  const items = [lowItem, highItem];
  const cs = new Map([['w:low', { A: 1.0, reps: 5 }]]);
  const st = new Map([['low1', { lastSec: now, reps: 5 }]]);
  const picked = pickItems(items, st, cs, 1, now, () => 0.5);
  assert.equal(picked[0].id, 'high1', '低桶題目在高中桶足量時不應被抽到');
});

test('高＋中不足時才納入低桶（否則會回傳不足額的題數）', () => {
  const now = 100 * DAY;
  // 只有一題，且落在低桶
  const lowItem = mkItem('low1', ['w:low']);
  const cs = new Map([['w:low', { A: 1.0, reps: 5 }]]);
  const st = new Map([['low1', { lastSec: now, reps: 5 }]]);
  const picked = pickItems([lowItem], st, cs, 1, now, () => 0.5);
  assert.equal(picked.length, 1, '高中不足額時應納入低桶，而非回傳不足額');
  assert.equal(picked[0].id, 'low1');
});

test('pickItems 為加權隨機而非排序取前 N', () => {
  const now = 100 * DAY;
  const items = [mkItem('a', ['w:a']), mkItem('b', ['w:b']), mkItem('c', ['w:c'])];
  // 三題皆從未考過（同權重 W=1.0，皆落高桶）——用不同 ΔT 製造權重差異更貼近真實情境
  const st = new Map([
    ['a', { lastSec: now - 1 * DAY, reps: 5 }],
    ['b', { lastSec: now - 7 * DAY, reps: 5 }],
    ['c', { lastSec: now - 30 * DAY, reps: 5 }],
  ]);
  const cs = new Map([['w:a', { A: 0.9, reps: 5 }], ['w:b', { A: 0.9, reps: 5 }], ['w:c', { A: 0.9, reps: 5 }]]);
  const late = pickItems(items, st, cs, 1, now, () => 0.999);
  const early = pickItems(items, st, cs, 1, now, () => 0.001);
  assert.notEqual(late[0].id, early[0].id, '不同亂數應抽到不同題目');
});

test('不重複抽到同一題', () => {
  const now = 100 * DAY;
  const items = [mkItem('a', ['w:a']), mkItem('b', ['w:b'])];
  const picked = pickItems(items, new Map(), new Map(), 2, now, () => 0.5);
  assert.equal(new Set(picked.map((i) => i.id)).size, 2);
});

test('要求數量超過可用題數時回傳全部，不無限迴圈', () => {
  const now = 100 * DAY;
  const items = [mkItem('a', ['w:a'])];
  assert.equal(pickItems(items, new Map(), new Map(), 10, now).length, 1);
});

test('新題比例上限：足量舊題可用時，新題數不得超過 30%', () => {
  const now = 100 * DAY;
  // 20 題全新（unseen，W=1.0，高桶），另 20 題已練得很熟但剛考過（W=0，低桶）——
  // 加上少量「舊但很久沒碰」的題目，確保舊題也落在高／中桶，足以填滿非新題名額。
  const freshItems = Array.from({ length: 20 }, (_, i) => mkItem('new' + i, ['w:new' + i]));
  const oldItems = Array.from({ length: 20 }, (_, i) => mkItem('old' + i, ['w:old' + i]));
  const items = [...freshItems, ...oldItems];
  const st = new Map(oldItems.map((it) => [it.id, { lastSec: now - 30 * DAY, reps: 5 }]));
  const cs = new Map(oldItems.map((it) => [it.covers[0], { A: 0.5, reps: 5 }]));
  const picked = pickItems(items, st, cs, 10, now, () => 0.999);
  const newCount = picked.filter((it) => it.id.startsWith('new')).length;
  assert.ok(newCount <= 3, `新題數應 ≤30%（3），實際 ${newCount}`);
  assert.equal(picked.length, 10);
});

test('本 session 已出現過的題目權重乘上 SESSION_SEEN_DECAY，避免同一輪重複被優先選中', () => {
  const now = 100 * DAY;
  const items = [mkItem('a', ['w:a']), mkItem('b', ['w:b'])];
  // 兩題原始權重相同（皆從未考過，W=1.0）；'a' 已在本 session 出現過，權重應被
  // 打到只剩 0.05／(0.05+1)≈4.8%，rng 落在中段時應抽到未衰減的 'b'。
  const picked = pickItems(items, new Map(), new Map(), 1, now, () => 0.5, new Set(['a']));
  assert.equal(picked[0].id, 'b');
  assert.equal(SCHED_CONST.SESSION_SEEN_DECAY, 0.05);
});

test('SCHED_CONST 集中常數：k / 分桶切點 / 新題上限', () => {
  assert.equal(SCHED_CONST.K_DAYS, 7);
  assert.equal(SCHED_CONST.BUCKET_HIGH, 1.0);
  assert.equal(SCHED_CONST.BUCKET_MID, 0.4);
  assert.equal(SCHED_CONST.NEW_ITEM_RATIO, 0.3);
});
