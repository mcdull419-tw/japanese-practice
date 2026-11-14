import { test } from 'node:test';
import assert from 'node:assert/strict';
import { answerHead, hintText } from '../../app/core/hint.js';

const lex = new Map([['銀行員', 'ぎんこういん'], ['山田', 'やまだ']]);

test('答案以假名開頭：直接給第一個字', () => {
  assert.equal(answerHead('おきて', lex), 'お');
});

test('答案以漢字開頭：給讀音的第一個假名，不給題幹上看得到的漢字', () => {
  const it = { prompt: { text: '食べます', hint: 'て形' }, answer: '食べて', answerKana: 'たべて' };
  assert.equal(hintText(it, lex), 'て形（開頭：た）');
});

test('沒有 answerKana 時查詞典', () => {
  assert.equal(answerHead('山田さんは 銀行員です。', lex), 'や');
});

test('「何」不在詞典也給な', () => {
  assert.equal(answerHead('何を 買いますか。', lex), 'な');
});

test('讀音查不到：不給開頭，只留題型說明', () => {
  const it = { prompt: { hint: '照範例的句型造句' }, answer: '鈴木さんです。' };
  assert.equal(hintText(it, lex), '照範例的句型造句');
});
