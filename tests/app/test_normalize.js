import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeAnswer, isCorrect } from '../../app/core/normalize.js';

test('格式差異一律寬鬆', () => {
  assert.ok(isCorrect('わたしはワープロで手紙を書きます', 'わたしは  ワープロで  手紙を  書きます。'));
  assert.ok(isCorrect('コーヒー', 'こーひー'));          // 片假名↔平假名
  assert.ok(isCorrect('たべます。', 'たべます'));         // 句號可有可無
  assert.ok(isCorrect('たべます.', 'たべます'));          // 半形句點
  assert.ok(isCorrect('１４にち', '14にち'));             // 全形數字
});

test('語言本身的差異一律嚴格', () => {
  assert.equal(isCorrect('きて', 'きって'), false);       // 促音
  assert.equal(isCorrect('ビル', 'ビール'), false);       // 長音
  assert.equal(isCorrect('かいて', 'かいで'), false);     // 濁音
});

test('alternatives 任一相符即正確', () => {
  assert.ok(isCorrect('から', 'に', ['から']));
  assert.equal(isCorrect('へ', 'に', ['から']), false);
});

test('normalizeAnswer 冪等', () => {
  const once = normalizeAnswer('わたしは  コーヒーを  飲みます。');
  assert.equal(normalizeAnswer(once), once);
});
