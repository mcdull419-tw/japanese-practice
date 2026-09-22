import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../app/generators/cloze.js';

const sentences = [
  { id: 'L07-文型-2', jp: 'わたしは  木村さんに  花を  あげます。', section: '文型', no: 2, lesson: 7, alt: [] },
  { id: 'L07-文型-3', jp: 'わたしは  カリナさんに  チョコレートを  もらいました。', section: '文型', no: 3, lesson: 7, alt: ['から'] },
];
const marks = {
  'L07-文型-2': [{ at: 10, p: 'に', c: 'p:ni:recipient' }],
  'L07-文型-3': [{ at: 11, p: 'に', c: 'p:ni:recipient' }],
};

test('挖掉助詞，題幹留下底線', () => {
  const it = [...generate(sentences, marks)].find((x) => x.id === 'cloze:L07-文型-2:10');
  assert.ok(it, '應產生 cloze:L07-文型-2:10');
  assert.equal(it.engine, 'cloze');
  assert.equal(it.prompt.text, 'わたしは  木村さん＿  花を  あげます。');
  assert.equal(it.answer, 'に');
  assert.deepEqual(it.covers, ['p:ni:recipient']);
  assert.deepEqual(it.skills, ['助詞']);
  assert.equal(it.lesson, 7);
  assert.equal(it.requires_lesson, 7);
  assert.equal(it.source_ref, '第7課 文型-2');
});

test('課本標註的替代形納入 alternatives（規格 §9.2 第一類）', () => {
  const it = [...generate(sentences, marks)].find((x) => x.id === 'cloze:L07-文型-3:11');
  assert.ok(it);
  assert.equal(it.answer, 'に');
  assert.ok(it.alternatives.includes('から'), '課本標的から 應算對');
});

test('方向助詞 へ↔に 互為替代（規格 §9.2 第二類）', () => {
  const s = [{ id: 'L05-文型-1', jp: 'わたしは  京都へ  行きます。', section: '文型', no: 1, lesson: 5, alt: [] }];
  const m = { 'L05-文型-1': [{ at: 8, p: 'へ', c: 'p:e:direction' }] };
  const it = [...generate(s, m)][0];
  assert.equal(it.answer, 'へ');
  assert.ok(it.alternatives.includes('に'), '方向的に 應算對');
});

test('授受來源 に↔から 互為替代，即使課本該句未標', () => {
  const s = [{ id: 'L07-例文-5', jp: '山田さんに  もらいました。', section: '例文', no: 5, lesson: 7, alt: [] }];
  const m = { 'L07-例文-5': [{ at: 4, p: 'に', c: 'p:ni:source' }] };
  const it = [...generate(s, m)][0];
  assert.ok(it.alternatives.includes('から'));
});

test('沒有標註的句子不產題（不猜）', () => {
  const s = [{ id: 'L01-文型-1', jp: 'わたしは  マイク・ミラーです。', section: '文型', no: 1, lesson: 1, alt: [] }];
  assert.equal([...generate(s, {})].length, 0);
});

test('標註指向不存在的句子時略過，不拋錯', () => {
  const items = [...generate(sentences, { 'L99-文型-1': [{ at: 0, p: 'に', c: 'p:ni:time' }] })];
  assert.equal(items.length, 0);
});

test('一句多個助詞各自成題，id 不撞', () => {
  const s = [{ id: 'L07-例文-1', jp: 'きのう  友達に  手紙を  書きました。', section: '例文', no: 1, lesson: 7, alt: [] }];
  const m = { 'L07-例文-1': [
    { at: 7, p: 'に', c: 'p:ni:recipient' },
    { at: 12, p: 'を', c: 'p:wo:object' },
  ] };
  const items = [...generate(s, m)];
  assert.equal(items.length, 2);
  assert.equal(new Set(items.map((x) => x.id)).size, 2);
  assert.equal(items[0].answer, 'に');
  assert.equal(items[1].answer, 'を');
  // 各題只挖自己那一個，另一個助詞要留在題幹裡
  assert.ok(items[0].prompt.text.includes('を'));
  assert.ok(items[1].prompt.text.includes('に'));
});

test('id 決定性：同一份輸入重跑結果相同', () => {
  const a = [...generate(sentences, marks)].map((x) => x.id);
  const b = [...generate(sentences, marks)].map((x) => x.id);
  assert.deepEqual(a, b);
});
test('詞組挖空：內容詞對得上 vocab 時才出題', () => {
  const s = [{ id: 'L07-文型-1', jp: 'わたしは  ワープロで  手紙を  書きます。', section: '文型', no: 1, lesson: 7, alt: [] }];
  const vocab = [{ kana: 'てがみ', kanji: '手紙', zh: '信', lesson: 7, no: 5 }];
  const items = [...generate(s, {}, vocab)];
  const it = items.find((x) => x.id === 'cloze:L07-文型-1:13:phrase');
  assert.ok(it, '手紙を 這個詞組應可出題');
  assert.equal(it.prompt.text, 'わたしは  ワープロで  ＿を  書きます。');
  assert.equal(it.answer, '手紙');
  assert.ok(it.alternatives.includes('てがみ'), '假名寫法應算對');
  assert.deepEqual(it.covers, ['w:手紙']);
  assert.deepEqual(it.skills, ['單字']);
  assert.equal(it.prompt.hint, '信');
});

test('詞組挖空：對不上 vocab 的詞組不出題', () => {
  const s = [{ id: 'L07-文型-1', jp: 'わたしは  ワープロで  手紙を  書きます。', section: '文型', no: 1, lesson: 7, alt: [] }];
  const items = [...generate(s, {}, [])];
  assert.equal(items.length, 0, 'vocab 空的時候不該產出任何詞組題');
});

test('詞組挖空與助詞挖空並存，id 不撞', () => {
  const s = [{ id: 'L07-文型-1', jp: 'わたしは  ワープロで  手紙を  書きます。', section: '文型', no: 1, lesson: 7, alt: [] }];
  const m = { 'L07-文型-1': [{ at: 15, p: 'を', c: 'p:wo:object' }] };
  const vocab = [{ kana: 'てがみ', kanji: '手紙', zh: '信', lesson: 7, no: 5 }];
  const ids = [...generate(s, m, vocab)].map((x) => x.id);
  assert.equal(new Set(ids).size, ids.length);
  assert.ok(ids.includes('cloze:L07-文型-1:15'));
  assert.ok(ids.includes('cloze:L07-文型-1:13:phrase'));
});

test('未提供 vocab 時只產助詞題（行為不變）', () => {
  const items = [...generate(sentences, marks)];
  assert.ok(items.every((x) => !x.id.endsWith(':phrase')));
});

test('詞組挖空：內容詞之後必須是助詞或詞組結尾，不切在詞中間', () => {
  const s = [{ id: 'L04-例文-1', jp: '山田さんは  何時に  寝ますか。', section: '例文', no: 1, lesson: 4, alt: [] }];
  const vocab = [
    { kana: 'やま', kanji: '山', zh: '山', lesson: 10, no: 1 },
    { kana: 'なに', kanji: '何', zh: '什麼', lesson: 2, no: 1 },
  ];
  const items = [...generate(s, {}, vocab)];
  assert.equal(items.length, 0, '山田 不該挖成 山、何時 不該挖成 何');
});

test('詞組挖空只取 文型 與 例文 段落（会話、問題 不是乾淨單句）', () => {
  const s = [
    { id: 'L01-会話-1', jp: '手紙を  書きます。', section: '会話', no: 1, lesson: 1, alt: [] },
    { id: 'L01-問題-1', jp: '手紙を  書きます。', section: '問題', no: 1, lesson: 1, alt: [] },
  ];
  const vocab = [{ kana: 'てがみ', kanji: '手紙', zh: '信', lesson: 1, no: 5 }];
  assert.equal([...generate(s, {}, vocab)].length, 0);
});
