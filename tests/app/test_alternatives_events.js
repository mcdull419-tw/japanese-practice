// 規格 §9.2.1／§10.1：自訂答案存在事件日誌的 `a` 欄位，不存 localStorage。
import test from 'node:test';
import assert from 'node:assert/strict';
import { makeEvent, userAlternativesFrom, MemoryStore } from '../../app/core/store.js';
import { migrateLegacyAlternatives } from '../../app/main.js';

test('makeEvent 不帶 alt 時，事件形狀與舊版完全相同（無 a 欄位）', () => {
  const e = makeEvent('a3f9', 1482, 'conj:かきます:masu2te', 3, 2400, 'text', 1757500000);
  assert.deepEqual(Object.keys(e).sort(), ['d', 'g', 'i', 'm', 'n', 'r', 't']);
  assert.equal('a' in e, false);
});

test('makeEvent 帶 alt 時多出 a 欄位，其餘欄位不變', () => {
  const e = makeEvent('a3f9', 1483, 'conj:送ります:masu2te', 3, 0, 'text', 1757500004, '送って');
  assert.equal(e.a, '送って');
  assert.equal(e.d, 'a3f9');
  assert.equal(e.n, 1483);
  assert.equal(e.g, 3);
});

test('從事件重建 alternatives', () => {
  const evs = [
    makeEvent('d', 1, 'x', 1, 100, 'text', 10),
    makeEvent('d', 2, 'x', 3, 0, 'text', 11, '送って'),
    makeEvent('d', 3, 'x', 3, 0, 'text', 12, '送りまして'),
    makeEvent('d', 4, 'y', 3, 0, 'text', 13, 'つま'),
  ];
  const alts = userAlternativesFrom(evs);
  assert.deepEqual(alts.get('x'), ['送って', '送りまして']);
  assert.deepEqual(alts.get('y'), ['つま']);
});

test('同一寫法重複認可不會重複列入', () => {
  const evs = [
    makeEvent('d', 1, 'x', 3, 0, 'text', 10, '送って'),
    makeEvent('d', 2, 'x', 3, 0, 'text', 11, '送って'),
  ];
  assert.deepEqual(userAlternativesFrom(evs).get('x'), ['送って']);
});

test('舊格式事件（無 a 欄位）可正常重放，不拋錯也不產生 alternatives', () => {
  const legacy = [
    { d: 'a3f9', n: 1, i: 'recall:あつい:zh2jp', t: 1757500000, g: 3, r: 2400, m: 'text' },
    { d: 'a3f9', n: 2, i: 'conj:送ります:masu2te', t: 1757500060, g: 1, r: 8000, m: 'text' },
  ];
  const alts = userAlternativesFrom(legacy);
  assert.equal(alts.size, 0);
});

// --- 遷移 ---

function fakeStorage(initial) {
  const map = new Map(Object.entries(initial));
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, v),
    removeItem: (k) => map.delete(k),
    has: (k) => map.has(k),
  };
}

const LEGACY_KEY = 'jp-practice-user-alternatives';

test('遷移：localStorage 的舊自訂答案補寫成事件並刪除該鍵', async () => {
  const storage = fakeStorage({
    [LEGACY_KEY]: JSON.stringify({ 'recall:つま／かない:zh2jp': ['つま'], x: ['あ', 'い'] }),
  });
  const store = new MemoryStore();
  const n = await migrateLegacyAlternatives(storage, store, 'dev1', -1);

  assert.equal(n, 3);
  const alts = userAlternativesFrom(await store.allEvents());
  assert.deepEqual(alts.get('recall:つま／かない:zh2jp'), ['つま']);
  assert.deepEqual(alts.get('x'), ['あ', 'い']);
  assert.equal(storage.has(LEGACY_KEY), false, '遷移後舊鍵必須刪除');
});

test('遷移：補寫的事件從 startSeq 之後接續編號，不與既有事件撞鍵', async () => {
  const storage = fakeStorage({ [LEGACY_KEY]: JSON.stringify({ x: ['あ'] }) });
  const store = new MemoryStore();
  await store.appendEvents([makeEvent('dev1', 7, 'x', 1, 100, 'text', 10)]);
  await migrateLegacyAlternatives(storage, store, 'dev1', 7);

  const evs = await store.allEvents();
  assert.equal(evs.length, 2, '既有事件不得被覆蓋');
  assert.deepEqual(evs.map((e) => e.n).sort((a, b) => a - b), [7, 8]);
});

test('遷移：沒有舊鍵時為無操作', async () => {
  const store = new MemoryStore();
  assert.equal(await migrateLegacyAlternatives(fakeStorage({}), store, 'dev1', -1), 0);
  assert.equal((await store.allEvents()).length, 0);
});

test('遷移：舊鍵內容毀損時不拋錯', async () => {
  const store = new MemoryStore();
  const storage = fakeStorage({ [LEGACY_KEY]: '{壞掉的 JSON' });
  assert.equal(await migrateLegacyAlternatives(storage, store, 'dev1', -1), 0);
});

test('遷移重跑一次不會產生重複事件（(d,n) 去重）', async () => {
  const raw = JSON.stringify({ x: ['あ'] });
  const store = new MemoryStore();
  await migrateLegacyAlternatives(fakeStorage({ [LEGACY_KEY]: raw }), store, 'dev1', -1);
  await migrateLegacyAlternatives(fakeStorage({ [LEGACY_KEY]: raw }), store, 'dev1', -1);
  assert.equal((await store.allEvents()).length, 1);
});

test('自訂答案會進入 exportJSON 的輸出（localStorage 版本的核心缺陷）', async () => {
  const store = new MemoryStore();
  await store.appendEvents([makeEvent('d', 1, 'x', 3, 0, 'text', 10, '送って')]);
  const dumped = JSON.parse(await store.exportJSON());
  assert.equal(dumped.events[0].a, '送って');
  assert.deepEqual(userAlternativesFrom(dumped.events).get('x'), ['送って']);
});
