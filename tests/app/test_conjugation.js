import { test } from 'node:test';
import assert from 'node:assert/strict';
import { conjugate, FORMS, FORM_LESSON } from '../../app/lang/conjugation.js';

test('時態四變化（與類別無關）', () => {
  assert.equal(conjugate('かきます', 'I', 'masu'), 'かきます');
  assert.equal(conjugate('かきます', 'I', 'masen'), 'かきません');
  assert.equal(conjugate('かきます', 'I', 'mashita'), 'かきました');
  assert.equal(conjugate('かきます', 'I', 'masendeshita'), 'かきませんでした');
  assert.equal(conjugate('たべます', 'II', 'masen'), 'たべません');
});

test('I 類て形：依語幹末音', () => {
  assert.equal(conjugate('かいます', 'I', 'te'), 'かって');   // い→って
  assert.equal(conjugate('まちます', 'I', 'te'), 'まって');   // ち→って
  assert.equal(conjugate('とります', 'I', 'te'), 'とって');   // り→って
  assert.equal(conjugate('のみます', 'I', 'te'), 'のんで');   // み→んで
  assert.equal(conjugate('あそびます', 'I', 'te'), 'あそんで'); // び→んで
  assert.equal(conjugate('かきます', 'I', 'te'), 'かいて');   // き→いて
  assert.equal(conjugate('いそぎます', 'I', 'te'), 'いそいで'); // ぎ→いで
  assert.equal(conjugate('はなします', 'I', 'te'), 'はなして'); // し→して
});

test('いきます 是唯一的 I 類て形不規則', () => {
  assert.equal(conjugate('いきます', 'I', 'te'), 'いって');
  assert.notEqual(conjugate('いきます', 'I', 'te'), 'いいて');
});

test('行きます 的漢字形也套用同一組不規則（修正 A：先前落到一般規則算出「行いて」）', () => {
  assert.equal(conjugate('行きます', 'I', 'te'), '行って');
  assert.notEqual(conjugate('行きます', 'I', 'te'), '行いて');
});

test('II 類與 III 類て形', () => {
  assert.equal(conjugate('たべます', 'II', 'te'), 'たべて');
  assert.equal(conjugate('おきます', 'II', 'te'), 'おきて');
  assert.equal(conjugate('します', 'III', 'te'), 'して');
  assert.equal(conjugate('きます', 'III', 'te'), 'きて');
  assert.equal(conjugate('べんきょうします', 'III', 'te'), 'べんきょうして');
});

test('外形像 II 類的 I 類動詞，依傳入的 group 變化', () => {
  // 帰ります 是 I 類：て形為 かえって，不是 かえて
  assert.equal(conjugate('かえります', 'I', 'te'), 'かえって');
  // 借ります 是 II 類：て形為 かりて，不是 かって
  assert.equal(conjugate('かります', 'II', 'te'), 'かりて');
});

test('無效輸入丟 Error，不得靜默回傳', () => {
  assert.throws(() => conjugate('たべる', 'II', 'te'), /ます/);
  assert.throws(() => conjugate('たべます', 'IV', 'te'), /group/);
  assert.throws(() => conjugate('たべます', 'II', 'nai'), /form/);
});

test('FORM_LESSON 標示各形態的解鎖課次', () => {
  assert.equal(FORM_LESSON.masu, 4);
  assert.equal(FORM_LESSON.te, 14);
  assert.ok(FORMS.includes('te'));
});
