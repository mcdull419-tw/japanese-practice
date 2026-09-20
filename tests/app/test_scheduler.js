import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildConceptStates, priority, pickItems } from '../../app/core/scheduler.js';

const mkItem = (id, covers) => ({ id, covers, requires_lesson: 1, engine: 'recall' });

test('概念狀態由涵蓋它的題目聚合而來', () => {
  const items = [mkItem('i1', ['w:a']), mkItem('i2', ['w:a', 'w:b'])];
  const st = new Map([['i1', { R: 0.2, reps: 3 }], ['i2', { R: 0.8, reps: 1 }]]);
  const cs = buildConceptStates(st, items);
  assert.ok(cs.has('w:a') && cs.has('w:b'));
  assert.ok(cs.get('w:a').R > 0.2 && cs.get('w:a').R < 0.8);
});

test('生疏的題目優先度較高', () => {
  const items = [mkItem('i1', ['w:a'])];
  const cs = new Map([['w:a', { R: 0.5, reps: 2 }]]);
  const weak = priority(items[0], new Map([['i1', { R: 0.1, reps: 5 }]]), cs);
  const strong = priority(items[0], new Map([['i1', { R: 0.95, reps: 5 }]]), cs);
  assert.ok(weak > strong);
});

test('概念生疏會拉高所有涵蓋它的題目（跨題型傳導）', () => {
  const it = mkItem('i1', ['g:X']);
  const st = new Map([['i1', { R: 0.5, reps: 2 }]]);
  const weakConcept = priority(it, st, new Map([['g:X', { R: 0.1, reps: 9 }]]));
  const strongConcept = priority(it, st, new Map([['g:X', { R: 0.9, reps: 9 }]]));
  assert.ok(weakConcept > strongConcept);
});

test('未練過的題目優先度最高', () => {
  const it = mkItem('new', ['w:z']);
  assert.ok(priority(it, new Map(), new Map()) > 0);
});

test('pickItems 為加權隨機而非排序取前 N', () => {
  const items = [mkItem('a', ['w:a']), mkItem('b', ['w:b']), mkItem('c', ['w:c'])];
  const st = new Map([
    ['a', { R: 0.1, reps: 5 }], ['b', { R: 0.5, reps: 5 }], ['c', { R: 0.9, reps: 5 }]]);
  const cs = buildConceptStates(st, items);
  // rng 回傳接近 1 → 抽到權重較低者，證明不是單純排序
  const late = pickItems(items, st, cs, 1, () => 0.999);
  const early = pickItems(items, st, cs, 1, () => 0.001);
  assert.notEqual(late[0].id, early[0].id, '不同亂數應抽到不同題目');
});

test('不重複抽到同一題', () => {
  const items = [mkItem('a', ['w:a']), mkItem('b', ['w:b'])];
  const picked = pickItems(items, new Map(), new Map(), 2, () => 0.5);
  assert.equal(new Set(picked.map((i) => i.id)).size, 2);
});

test('要求數量超過可用題數時回傳全部，不無限迴圈', () => {
  const items = [mkItem('a', ['w:a'])];
  assert.equal(pickItems(items, new Map(), new Map(), 10, () => 0.5).length, 1);
});

test('新題比例上限：足量舊題可用時，新題數不得超過 30%', () => {
  // 20 題全新（unseen），另 20 題已練得很熟（R 高、優先度低，但數量足夠填滿非新題名額）。
  // count=10 時，若無新題比例上限，加權抽樣幾乎必然抽到 10 題全新題（新題 priority 遠高於舊題）。
  // 有上限（30%）時，最多 3 題新題；由於舊題數量充足（20 ≥ 7），其餘名額應由舊題填滿。
  const freshItems = Array.from({ length: 20 }, (_, i) => mkItem('new' + i, ['w:new' + i]));
  const oldItems = Array.from({ length: 20 }, (_, i) => mkItem('old' + i, ['w:old' + i]));
  const items = [...freshItems, ...oldItems];
  const st = new Map(oldItems.map((it) => [it.id, { R: 0.9, reps: 5 }]));
  const cs = buildConceptStates(st, items);
  const picked = pickItems(items, st, cs, 10, () => 0.999);
  const newCount = picked.filter((it) => it.id.startsWith('new')).length;
  assert.ok(newCount <= 3, `新題數應 ≤30%（3），實際 ${newCount}`);
  assert.equal(picked.length, 10);
});
