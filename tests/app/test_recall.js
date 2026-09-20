import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate, ENGINE } from '../../app/generators/recall.js';

const V = [
  { kana: 'きります', kanji: '切ります', zh: '剪，切', lesson: 7, category: 'numbered', group: null },
  { kana: 'あげます', kanji: null, zh: '給，送', lesson: 7, category: 'numbered', group: null },
];

test('有漢字者產生兩題，無漢字者只產生一題', () => {
  const items = [...generate(V)];
  const ids = items.map((i) => i.id);
  assert.ok(ids.includes('recall:きります:zh2jp'));
  assert.ok(ids.includes('recall:きります:kanji2kana'));
  assert.ok(ids.includes('recall:あげます:zh2jp'));
  assert.equal(ids.includes('recall:あげます:kanji2kana'), false);
  assert.equal(items.length, 3);
});

test('zh2jp：題幹為中文，答案為假名，漢字列入 alternatives', () => {
  const it = [...generate(V)].find((i) => i.id === 'recall:きります:zh2jp');
  assert.equal(it.prompt.text, '剪，切');
  assert.equal(it.answer, 'きります');
  assert.ok(it.alternatives.includes('切ります'));
  assert.equal(it.engine, ENGINE);
});

test('kanji2kana：考讀音，covers 含 reading 概念', () => {
  const it = [...generate(V)].find((i) => i.id === 'recall:きります:kanji2kana');
  assert.equal(it.prompt.text, '切ります');
  assert.equal(it.answer, 'きります');
  assert.ok(it.covers.includes('w:きります:reading'));
  assert.ok(it.skills.includes('讀音'));
  assert.deepEqual(it.alternatives, [], '考讀音時不接受漢字作答');
});

test('requires_lesson 等於單字所在課次，source_ref 可讀', () => {
  const it = [...generate(V)][0];
  assert.equal(it.requires_lesson, 7);
  assert.ok(it.source_ref.includes('第7課'));
});

test('重新生成得到相同 id（決定性）', () => {
  const a = [...generate(V)].map((i) => i.id);
  const b = [...generate(V)].map((i) => i.id);
  assert.deepEqual(a, b);
});
