import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../app/generators/substitute.js';

const patterns = [{
  id: 'L07-A1',
  lesson: 7,
  requires_lesson: 7,
  template: '{S}は{T}で ごはんを 食べます。',
  slots: { S: ['日本人', 'インドネシア人', 'アメリカ人'], T: ['はし', 'スプーンと フォーク', 'ナイフと フォーク'] },
  rows: [[0, 0], [1, 1], [2, 2]],
  question_variant: '日本人はなんで ごはんを 食べますか。',
}];
const concepts = new Map([['L07-A1', ['g:de_means']]]);

test('逐列展開代入表', () => {
  const items = [...generate(patterns, concepts)];
  assert.equal(items.length, 3);
  const it = items.find((x) => x.id === 'subst:L07-A1:1');
  assert.ok(it);
  assert.equal(it.engine, 'substitute');
  assert.equal(it.answer, 'インドネシア人はスプーンと フォークで ごはんを 食べます。');
  assert.equal(it.lesson, 7);
  assert.equal(it.requires_lesson, 7);
  assert.equal(it.source_ref, '第7課 練習Ａ-1');
});

test('題幹給出範例句與本題的提示詞', () => {
  const it = [...generate(patterns, concepts)].find((x) => x.id === 'subst:L07-A1:1');
  // 範例取第0列，讓使用者知道要造什麼樣的句子
  assert.ok(it.prompt.text.includes('日本人ははしで ごはんを 食べます。'), '應含第0列範例');
  assert.ok(it.prompt.text.includes('インドネシア人'), '應含本題提示詞');
  assert.ok(it.prompt.text.includes('スプーンと フォーク'), '應含本題提示詞');
});

test('第 0 列本身也出題，但題幹改用第 1 列當範例', () => {
  const it = [...generate(patterns, concepts)].find((x) => x.id === 'subst:L07-A1:0');
  assert.ok(it, '第0列也該出題');
  assert.equal(it.answer, '日本人ははしで ごはんを 食べます。');
  assert.ok(it.prompt.text.includes('インドネシア人はスプーンと フォークで'), '範例應改用第1列');
  assert.ok(!it.prompt.text.includes('日本人ははしで ごはんを 食べます。'), '範例不得等於答案');
});

test('covers 含句型概念與各槽位填充詞', () => {
  const it = [...generate(patterns, concepts)].find((x) => x.id === 'subst:L07-A1:1');
  assert.ok(it.covers.includes('g:de_means'), '應含句型概念');
  assert.ok(it.skills.includes('句型'));
});

test('沒有對應概念的代入表仍出題，以表 id 當概念（不靜默丟棄素材）', () => {
  const it = [...generate(patterns, new Map())][0];
  assert.ok(it, '無概念對應時仍應出題');
  assert.deepEqual(it.covers, ['g:L07-A1']);
});

test('只有一列的表不出題（沒有代入的變化可練）', () => {
  const single = [{ ...patterns[0], id: 'L07-A9', rows: [[0, 0]] }];
  assert.equal([...generate(single, new Map())].length, 0);
});

test('槽位索引越界時略過該列，不產生壞題目', () => {
  // 需要至少兩列有效才有「範例≠答案」可言，因此用三列、其中一列越界。
  const bad = [{ ...patterns[0], id: 'L07-A8', rows: [[0, 0], [9, 9], [1, 1]] }];
  const items = [...generate(bad, new Map())];
  assert.equal(items.length, 2);
  assert.deepEqual(items.map((x) => x.id), ['subst:L07-A8:0', 'subst:L07-A8:2']);
  assert.ok(items.every((x) => !x.answer.includes('undefined')));
  // 第0列的範例不得因第1列越界而消失，改取下一個有效列
  assert.ok(items[0].prompt.text.includes('インドネシア人'));
});

test('id 決定性且唯一', () => {
  const a = [...generate(patterns, concepts)].map((x) => x.id);
  const b = [...generate(patterns, concepts)].map((x) => x.id);
  assert.deepEqual(a, b);
  assert.equal(new Set(a).size, a.length);
});
