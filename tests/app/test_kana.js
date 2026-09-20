import { test } from 'node:test';
import assert from 'node:assert/strict';
import { toHiragana, toKatakana, isKana, stripSpaces } from '../../app/lang/kana.js';

test('片假名轉平假名', () => {
  assert.equal(toHiragana('コーヒー'), 'こーひー');
  assert.equal(toHiragana('きります'), 'きります');
  assert.equal(toHiragana('切ります'), '切ります');   // 漢字不動
});

test('平假名轉片假名', () => {
  assert.equal(toKatakana('きります'), 'キリマス');
  assert.equal(toKatakana('コーヒー'), 'コーヒー');   // 已是片假名，不動
});

test('isKana 判定', () => {
  assert.equal(isKana('あ'), true);
  assert.equal(isKana('ア'), true);
  assert.equal(isKana('切'), false);
  assert.equal(isKana('A'), false);
});

test('stripSpaces 移除半形與全形空白', () => {
  assert.equal(stripSpaces('わたしは  ワープロで'), 'わたしはワープロで');
  assert.equal(stripSpaces('あの　ひと'), 'あのひと');   // 全形空白 U+3000
});
