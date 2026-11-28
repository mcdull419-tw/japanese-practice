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

test('〔 〕與［ ］一樣是可省略的部分', () => {
  const it = { id: 'x', answer: 'いろいろ〔な〕' };
  assert.equal(gradeAnswer('いろいろ', it, 1000, 0, false).correct, true);
  assert.equal(gradeAnswer('いろいろな', it, 1000, 0, false).correct, true);
  const it2 = { id: 'y', answer: '〔どうも〕すみません。' };
  assert.equal(gradeAnswer('すみません', it2, 1000, 0, false).correct, true);
  assert.equal(gradeAnswer('どうもすみません', it2, 1000, 0, false).correct, true);
});

test('引號「」『』“” 打不打都算對', () => {
  const it = { id: 'x', answer: '「ありがとう」はえいごで“Thank you”です。' };
  assert.equal(gradeAnswer('ありがとうはえいごでThank youです', it, 1000, 0, false).correct, true);
  assert.equal(gradeAnswer('「ありがとう」はえいごで“Thank you”です。', it, 1000, 0, false).correct, true);
  const it2 = { id: 'y', answer: '「七人の 侍」は どんな 映画ですか。 おもしろい 映画です。' };
  assert.equal(gradeAnswer('七人の侍はどんな映画ですか。おもしろい映画です。', it2, 1000, 0, false).correct, true);
  const it3 = { id: 'z', answer: '「しちにんのさむらい」', strictKana: true };
  assert.equal(gradeAnswer('しちにんのさむらい', it3, 1000, 0, false).correct, true);
});

// 答案對到「其他也算對的答案」而不是課本答案時，結果畫面要說明，
// 否則「正確」下面印著「正解：へ」，看起來像判錯（例：日本＿来ました 寫 に）。
const cloze = { answer: 'へ', alternatives: ['に'] };

test('寫課本答案：不標示為其他寫法', () => {
  assert.equal(gradeAnswer('へ', cloze, 1, 1, false).viaAlternative, false);
});

test('寫其他也算對的答案：答對並標示為其他寫法', () => {
  const r = gradeAnswer('に', cloze, 1, 1, false);
  assert.equal(r.correct, true);
  assert.equal(r.viaAlternative, true);
});

test('答錯時不標示為其他寫法', () => {
  assert.equal(gradeAnswer('で', cloze, 1, 1, false).viaAlternative, false);
});

test('課本答案的可省略部分省掉不算其他寫法', () => {
  assert.equal(gradeAnswer('しずか', { answer: 'しずか［な］' }, 1, 1, false).viaAlternative, false);
});
