import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeEvent, mergeEvents, MemoryStore } from '../../app/core/store.js';

test('事件使用短鍵，含裝置 id 與序號', () => {
  const e = makeEvent('a3f9', 1482, 'conj:かきます:masu2te', 3, 2400, 'text', 1757500000);
  assert.deepEqual(e, {
    d: 'a3f9', n: 1482, i: 'conj:かきます:masu2te',
    t: 1757500000, g: 3, r: 2400, m: 'text',
  });
});

test('合併以 (d,n) 去重，而非 (i,t)', () => {
  const same = { d: 'a', n: 1, i: 'x', t: 100, g: 3, r: 0, m: 'text' };
  const dupe = { ...same };
  assert.equal(mergeEvents([same], [dupe]).length, 1, '同一 (d,n) 應去重');

  // 同一題、同一秒、不同裝置 → 兩筆都必須保留
  const devA = { d: 'a', n: 1, i: 'x', t: 100, g: 3, r: 0, m: 'text' };
  const devB = { d: 'b', n: 1, i: 'x', t: 100, g: 1, r: 0, m: 'text' };
  assert.equal(mergeEvents([devA], [devB]).length, 2);

  // 同一裝置、同一題、同一秒、不同序號 → 連續作答兩次，都必須保留
  const n1 = { d: 'a', n: 1, i: 'x', t: 100, g: 1, r: 0, m: 'text' };
  const n2 = { d: 'a', n: 2, i: 'x', t: 100, g: 3, r: 0, m: 'text' };
  assert.equal(mergeEvents([n1], [n2]).length, 2);
});

test('合併結果依時間排序', () => {
  const out = mergeEvents(
    [{ d: 'a', n: 2, i: 'x', t: 200, g: 3, r: 0, m: 'text' }],
    [{ d: 'a', n: 1, i: 'x', t: 100, g: 3, r: 0, m: 'text' }],
  );
  assert.deepEqual(out.map((e) => e.t), [100, 200]);
});

test('MemoryStore 追加與讀取', async () => {
  const s = new MemoryStore();
  await s.appendEvents([makeEvent('a', 1, 'x', 3, 100, 'text', 1000)]);
  await s.appendEvents([makeEvent('a', 2, 'y', 1, 200, 'text', 2000)]);
  const all = await s.allEvents();
  assert.equal(all.length, 2);
});

test('匯出後匯入還原（含去重，不會因重複匯入而膨脹）', async () => {
  const s = new MemoryStore();
  await s.appendEvents([makeEvent('a', 1, 'x', 3, 100, 'text', 1000)]);
  const json = await s.exportJSON();
  await s.importJSON(json);
  await s.importJSON(json);
  assert.equal((await s.allEvents()).length, 1, '重複匯入不得產生重複事件');
});
