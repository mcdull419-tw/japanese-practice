import { test } from 'node:test';
import assert from 'node:assert/strict';
import { conjugateAdj, conjugateAdjAlts, FORMS, FORM_LESSON } from '../../app/lang/adjective.js';

test('い形容詞四變化', () => {
  assert.equal(conjugateAdj('大きい', 'i', 'plain'), '大きいです');
  assert.equal(conjugateAdj('大きい', 'i', 'neg'), '大きくないです');
  assert.equal(conjugateAdj('大きい', 'i', 'past'), '大きかったです');
  assert.equal(conjugateAdj('大きい', 'i', 'pastneg'), '大きくなかったです');
});

test('い形容詞て形與副詞形', () => {
  assert.equal(conjugateAdj('大きい', 'i', 'te'), '大きくて');
  assert.equal(conjugateAdj('大きい', 'i', 'adverb'), '大きく');
});

test('いい 是不規則：語幹改用 よ', () => {
  assert.equal(conjugateAdj('いい', 'i', 'plain'), 'いいです');
  assert.equal(conjugateAdj('いい', 'i', 'neg'), 'よくないです');
  assert.equal(conjugateAdj('いい', 'i', 'past'), 'よかったです');
  assert.equal(conjugateAdj('いい', 'i', 'pastneg'), 'よくなかったです');
  assert.equal(conjugateAdj('いい', 'i', 'te'), 'よくて');
  assert.equal(conjugateAdj('いい', 'i', 'adverb'), 'よく');
  assert.notEqual(conjugateAdj('いい', 'i', 'past'), 'いかったです');
});

test('複合形容詞含 いい 時只有語尾變（かっこいい）', () => {
  assert.equal(conjugateAdj('かっこいい', 'i', 'past'), 'かっこよかったです');
});

test('な形容詞四變化', () => {
  assert.equal(conjugateAdj('きれい', 'na', 'plain'), 'きれいです');
  assert.equal(conjugateAdj('きれい', 'na', 'neg'), 'きれいじゃありません');
  assert.equal(conjugateAdj('きれい', 'na', 'past'), 'きれいでした');
  assert.equal(conjugateAdj('きれい', 'na', 'pastneg'), 'きれいじゃありませんでした');
});

test('な形容詞て形與副詞形', () => {
  assert.equal(conjugateAdj('静か', 'na', 'te'), '静かで');
  assert.equal(conjugateAdj('静か', 'na', 'adverb'), '静かに');
});

test('な形容詞的 では 寫法列為可接受', () => {
  assert.deepEqual(conjugateAdjAlts('きれい', 'na', 'neg'), ['きれいではありません']);
  assert.deepEqual(conjugateAdjAlts('きれい', 'na', 'pastneg'), ['きれいではありませんでした']);
});

test('い形容詞的 ありません 寫法列為可接受', () => {
  assert.deepEqual(conjugateAdjAlts('大きい', 'i', 'neg'), ['大きくありません']);
  assert.deepEqual(conjugateAdjAlts('大きい', 'i', 'pastneg'), ['大きくありませんでした']);
});

test('無其他寫法時回傳空陣列', () => {
  assert.deepEqual(conjugateAdjAlts('大きい', 'i', 'past'), []);
  assert.deepEqual(conjugateAdjAlts('静か', 'na', 'te'), []);
});

test('參數不合法時拋錯', () => {
  assert.throws(() => conjugateAdj('大きい', 'i', 'nope'));
  assert.throws(() => conjugateAdj('大きい', 'x', 'past'));
  assert.throws(() => conjugateAdj('大き', 'i', 'past'));  // い形容詞必須以い結尾
});

test('FORM_LESSON 覆蓋全部 FORMS，過去式為第12課', () => {
  for (const f of FORMS) assert.equal(typeof FORM_LESSON[f], 'number');
  assert.equal(FORM_LESSON.plain, 8);
  assert.equal(FORM_LESSON.past, 12);
  assert.equal(FORM_LESSON.te, 16);
});
