import { test } from 'node:test';
import assert from 'node:assert/strict';
import { watchForUpdate, checkWhenVisible } from '../../app/ui/update.js';

function fakeContainer(controller) {
  const t = new EventTarget();
  t.controller = controller;
  return t;
}
const change = (t) => t.dispatchEvent(new Event('controllerchange'));

test('已有舊版控制頁面時，新版接手就提示，且只提示一次', () => {
  const c = fakeContainer({});
  let n = 0;
  watchForUpdate(c, () => n++);
  change(c); change(c);
  assert.equal(n, 1);
});

test('第一次安裝（原本沒有控制者）不提示——那不是更新', () => {
  const c = fakeContainer(null);
  let n = 0;
  watchForUpdate(c, () => n++);
  change(c);
  assert.equal(n, 0);
});

test('不支援 Service Worker 的環境不炸', () => {
  assert.doesNotThrow(() => watchForUpdate(undefined, () => {}));
});

test('回到前景時才檢查更新，進背景不檢查', () => {
  const doc = new EventTarget();
  let calls = 0;
  checkWhenVisible(doc, { update: () => { calls++; return Promise.resolve(); } });
  doc.visibilityState = 'hidden'; doc.dispatchEvent(new Event('visibilitychange'));
  assert.equal(calls, 0);
  doc.visibilityState = 'visible'; doc.dispatchEvent(new Event('visibilitychange'));
  assert.equal(calls, 1);
});

import { describeVersion, forceRefresh } from '../../app/ui/update.js';

test('describeVersion：快取與程式同版本時不警告', async () => {
  const t = await describeVersion({ keys: async () => ['jp-practice-v7'] }, 'v7');
  assert.equal(t, '版本 v7｜離線快取 v7');
});

test('describeVersion：快取版本不同（或同時留著舊的）就提示重新下載', async () => {
  assert.match(await describeVersion({ keys: async () => ['jp-practice-v6'] }, 'v7'), /與程式不符/);
  assert.match(await describeVersion({ keys: async () => ['jp-practice-v6', 'jp-practice-v7'] }, 'v7'), /與程式不符/);
});

test('describeVersion：沒有快取支援時不炸', async () => {
  assert.equal(await describeVersion(undefined, 'v7'), '版本 v7｜離線快取 無');
});

test('forceRefresh：解除 SW、刪光快取、重新載入，且不碰 IndexedDB／localStorage', async () => {
  const log = [];
  const win = {
    navigator: { serviceWorker: { getRegistrations: async () => [{ unregister: async () => log.push('unreg') }] } },
    caches: { keys: async () => ['a', 'b'], delete: async (k) => log.push(`del ${k}`) },
    location: { reload: () => log.push('reload') },
    indexedDB: { deleteDatabase: () => log.push('DB!') },
    localStorage: { clear: () => log.push('LS!') },
  };
  await forceRefresh(win);
  assert.deepEqual(log, ['unreg', 'del a', 'del b', 'reload']);
});

test('forceRefresh：SW 或快取 API 丟錯也要走到重新載入', async () => {
  let reloaded = false;
  await forceRefresh({
    navigator: { serviceWorker: { getRegistrations: async () => { throw new Error('x'); } } },
    caches: { keys: async () => { throw new Error('y'); } },
    location: { reload: () => { reloaded = true; } },
  });
  assert.ok(reloaded);
});
