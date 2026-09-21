import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate, ENGINE } from '../../app/generators/recall.js';
import { isCorrect } from '../../app/core/normalize.js';

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

test('kanji2kana：考讀音，covers 含 reading 概念（概念以引用形為 lemma）', () => {
  const it = [...generate(V)].find((i) => i.id === 'recall:きります:kanji2kana');
  assert.equal(it.prompt.text, '切ります');
  assert.equal(it.answer, 'きります');
  // 概念層以引用形（漢字優先）為 lemma，故 covers 是 w:切ります:reading，
  // 不是 w:きります:reading——item id 與 concept id 是不同命名空間。
  assert.ok(it.covers.includes('w:切ります:reading'));
  assert.ok(it.skills.includes('讀音'));
  assert.deepEqual(it.alternatives, [], '考讀音時不接受漢字作答');
});

test('requires_lesson 等於單字所在課次，source_ref 可讀', () => {
  const it = [...generate(V)][0];
  assert.equal(it.requires_lesson, 7);
  assert.ok(it.source_ref.includes('第7課'));
});

test('漢字欄用分隔符列出多個寫法時，各寫法各自成為 alternative，原始整串也保留（修正 B）', () => {
  const multi = [{ kana: 'つくります', kanji: '作ります、造ります', zh: '做，製造', lesson: 15, no: 5 }];
  const it = [...generate(multi)].find((i) => i.id === 'recall:つくります:zh2jp');
  assert.ok(it.alternatives.includes('作ります'));
  assert.ok(it.alternatives.includes('造ります'));
  assert.ok(it.alternatives.includes('作ります、造ります'), '原始整串也保留');
  assert.ok(isCorrect('作ります', it.answer, it.alternatives), '只打其中一個寫法應算對');
  assert.ok(isCorrect('造ります', it.answer, it.alternatives), '打另一個寫法也應算對');
});

test('kanji2kana 題不受漢字分隔符拆分影響，alternatives 維持空陣列（考讀音時不接受漢字）', () => {
  const multi = [{ kana: 'あつい', kanji: '暑い、熱い', zh: '熱', lesson: 8, no: 1 }];
  const it = [...generate(multi)].find((i) => i.id === 'recall:あつい:kanji2kana');
  assert.equal(it.prompt.text, '暑い、熱い');
  assert.deepEqual(it.alternatives, []);
});

test('假名欄用分隔符列出多個說法時，各說法各自成為 alternative，只打其中一種也算對', () => {
  const multi = [{ kana: 'おっと／しゅじん', kanji: '夫／主人', zh: '丈夫', lesson: 9, no: 1 }];
  const it = [...generate(multi)].find((i) => i.id === 'recall:おっと／しゅじん:zh2jp');
  assert.ok(it.alternatives.includes('おっと'));
  assert.ok(it.alternatives.includes('しゅじん'));
  assert.ok(isCorrect('おっと', it.answer, it.alternatives), '只打其中一種假名說法應算對');
  assert.ok(isCorrect('しゅじん', it.answer, it.alternatives), '打另一種假名說法也應算對');
});

test('假名欄用分隔符列出三個以上說法時同樣全部算對（公司名例）', () => {
  const multi = [{ kana: 'IMC／パワーでんき／ブラジルエアー', kanji: 'IMC／パワー電気／ブラジルエアー', zh: '公司名', lesson: 1, no: null }];
  const it = [...generate(multi)].find((i) => i.id === 'recall:IMC／パワーでんき／ブラジルエアー:zh2jp');
  assert.ok(isCorrect('IMC', it.answer, it.alternatives));
  assert.ok(isCorrect('パワーでんき', it.answer, it.alternatives));
  assert.ok(isCorrect('ブラジルエアー', it.answer, it.alternatives));
});

test('假名欄含句子標點「、」時不得被拆開（那是標點，不是多種說法）', () => {
  const sentence = [{ kana: 'いいえ、けっこうです。', kanji: null, zh: '不用了，夠了。', lesson: 8, no: null }];
  const it = [...generate(sentence)].find((i) => i.id === 'recall:いいえ、けっこうです。:zh2jp');
  assert.deepEqual(it.alternatives, ['いいえ、けっこうです。'], '不含「、」切開後的片段');
  assert.equal(isCorrect('いいえ', it.answer, it.alternatives), false, '句子標點拆出的片段不該算對');
  assert.ok(isCorrect('いいえ、けっこうです。', it.answer, it.alternatives), '完整句子仍算對');
});

test('重新生成得到相同 id（決定性）', () => {
  const a = [...generate(V)].map((i) => i.id);
  const b = [...generate(V)].map((i) => i.id);
  assert.deepEqual(a, b);
});
