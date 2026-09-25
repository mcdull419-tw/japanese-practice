import { test } from 'node:test';
import assert from 'node:assert/strict';
import { isImeComposing } from '../../app/ui/session.js';

test('組字中的 Enter（isComposing）不算送出', () => {
  assert.equal(isImeComposing({ key: 'Enter', isComposing: true }), true);
});

test('舊版瀏覽器以 keyCode 229 表示組字中', () => {
  assert.equal(isImeComposing({ key: 'Enter', keyCode: 229 }), true);
});

test('組字結束後的 Enter 是真的送出', () => {
  assert.equal(isImeComposing({ key: 'Enter', isComposing: false, keyCode: 13 }), false);
});

test('欄位不存在時不誤判為組字中（否則永遠送不出去）', () => {
  assert.equal(isImeComposing({ key: 'Enter' }), false);
});
