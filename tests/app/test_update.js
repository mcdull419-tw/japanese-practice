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
