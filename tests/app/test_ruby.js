import { test } from 'node:test';
import assert from 'node:assert/strict';
import { annotateWithMarks } from '../../app/core/ruby.js';

test('依標註切出 text 與 ruby 交錯的 token', () => {
  const text = 'わたしは  ワープロで  手紙を  書きます。';
  const marks = [
    { at: 13, base: '手紙', kana: 'てがみ' },
    { at: 18, base: '書', kana: 'か' },
  ];
  assert.deepEqual(annotateWithMarks(text, marks), [
    { t: 'text', s: 'わたしは  ワープロで  ' },
    { t: 'ruby', base: '手紙', kana: 'てがみ' },
    { t: 'text', s: 'を  ' },
    { t: 'ruby', base: '書', kana: 'か' },
    { t: 'text', s: 'きます。' },
  ]);
});

test('沒有標註時回傳單一 text token', () => {
  assert.deepEqual(annotateWithMarks('これは 本です。', []), [{ t: 'text', s: 'これは 本です。' }]);
});

test('標註位置對不上文字時跳過該筆，不拋錯也不錯位', () => {
  const marks = [{ at: 3, base: '手紙', kana: 'てがみ' }]; // at 指到的不是 手紙
  assert.deepEqual(annotateWithMarks('これは 本です。', marks), [{ t: 'text', s: 'これは 本です。' }]);
});

test('標註未依 at 排序時仍正確切詞', () => {
  const marks = [
    { at: 18, base: '書', kana: 'か' },
    { at: 13, base: '手紙', kana: 'てがみ' },
  ];
  const tokens = annotateWithMarks('わたしは  ワープロで  手紙を  書きます。', marks);
  assert.deepEqual(tokens.filter((t) => t.t === 'ruby').map((t) => t.base), ['手紙', '書']);
});

test('空字串與非字串輸入回傳空陣列', () => {
  assert.deepEqual(annotateWithMarks('', []), []);
  assert.deepEqual(annotateWithMarks(null, []), []);
});
