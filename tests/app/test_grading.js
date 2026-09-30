import { test } from 'node:test';
import assert from 'node:assert/strict';
import { gradeAnswer } from '../../app/core/grading.js';

const item = { answer: 'きります', alternatives: ['切ります'] };

test('答錯一律 grade 1', () => {
  const r = gradeAnswer('たべます', item, 1000, 3000, false);
  assert.equal(r.correct, false);
  assert.equal(r.grade, 1);
});

test('答對且很快 → grade 4', () => {
  assert.equal(gradeAnswer('きります', item, 1000, 3000, false).grade, 4);
});

test('答對、速度普通 → grade 3', () => {
  assert.equal(gradeAnswer('きります', item, 3000, 3000, false).grade, 3);
});

test('答對但很慢 → grade 2', () => {
  assert.equal(gradeAnswer('きります', item, 9000, 3000, false).grade, 2);
});

test('用過提示即使答對也只給 grade 2', () => {
  assert.equal(gradeAnswer('きります', item, 500, 3000, true).grade, 2);
});

test('alternatives 亦視為答對', () => {
  assert.equal(gradeAnswer('切ります', item, 3000, 3000, false).correct, true);
});

test('沒有中位數可參考時（首次練該題型）給 grade 3', () => {
  assert.equal(gradeAnswer('きります', item, 1000, null, false).grade, 3);
});

// ── 選擇題（jp2zh）也走同一條評分路徑（規格 §11：判斷不得寫進 ui／engines）──
test('選擇題：選到正解判對', () => {
  const item = { answer: '剪，切', alternatives: [], choices: ['剪，切', '寄送', '借出', '給，送'] };
  assert.equal(gradeAnswer('剪，切', item, 1000, 2000, false).correct, true);
});

test('選擇題：沒選就送出判錯，不當成答對', () => {
  const item = { answer: '剪，切', alternatives: [], choices: ['剪，切', '寄送', '借出', '給，送'] };
  const r = gradeAnswer('', item, 1000, 2000, false);
  assert.equal(r.correct, false);
  assert.equal(r.grade, 1);
});

test('選擇題的中文選項不受假名正規化影響', () => {
  const item = { answer: '接受，得到', alternatives: [], choices: [] };
  assert.equal(gradeAnswer('接受，得到', item, 1000, 2000, false).correct, true);
  assert.equal(gradeAnswer('給，送', item, 1000, 2000, false).correct, false);
});
