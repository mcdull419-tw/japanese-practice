import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../app/generators/transform.js';

const V = [
  { kana: 'おくります', kanji: '送ります', zh: '寄送', lesson: 7, no: 2 },
  { kana: 'たべます', kanji: '食べます', zh: '吃', lesson: 6, no: 1 },
  { kana: 'きります', kanji: '切ります', zh: '剪，切', lesson: 7, no: 1 },
];
const VERBS = {
  送ります: { group: 'I', dict: '送る', kana: 'おくります' },
  食べます: { group: 'II', dict: '食べる', kana: 'たべます' },
  切ります: { group: 'I', dict: '切る', kana: 'きります' },
};

// 注意：id 與 covers 一律用引用形（v.kanji || v.kana），不是假名——
// 全語料的 おきます 同時對應 起きます（II類）與 置きます（I類），
// 若用假名當 id，兩個不同動詞會撞出相同 id（見 app/generators/transform.js 開頭註解）。
// 這裡的測試資料每個詞都有 kanji，所以引用形就是 kanji 欄位：
// 送ります(おくります)、食べます(たべます)、切ります(きります)。

test('每個動詞產生四種變化題', () => {
  const items = [...generate(V, VERBS)];
  const ids = items.filter((i) => i.id.startsWith('conj:送ります')).map((i) => i.id);
  assert.deepEqual(ids.sort(), [
    'conj:送ります:masu2masen',
    'conj:送ります:masu2masendeshita',
    'conj:送ります:masu2mashita',
    'conj:送ります:masu2te',
  ]);
});

test('て形題的答案正確，且 requires_lesson 取形態的解鎖課次', () => {
  const it = [...generate(V, VERBS)].find((i) => i.id === 'conj:送ります:masu2te');
  assert.equal(it.prompt.text, 'おくります');
  assert.equal(it.prompt.hint, 'て形');
  assert.equal(it.answer, 'おくって');
  assert.equal(it.lesson, 7, '單字出自第 7 課');
  assert.equal(it.requires_lesson, 14, 'て形第 14 課才教');
});

test('時態題的 requires_lesson 為單字課次（ます形第 4 課已教）', () => {
  const it = [...generate(V, VERBS)].find((i) => i.id === 'conj:食べます:masu2mashita');
  assert.equal(it.answer, 'たべました');
  assert.equal(it.requires_lesson, 6);
});

test('covers 含變化規則與該動詞的分類，skills 為「變化」', () => {
  const it = [...generate(V, VERBS)].find((i) => i.id === 'conj:切ります:masu2te');
  assert.equal(it.answer, 'きって');
  assert.ok(it.covers.includes('r:te:groupI'));
  assert.ok(it.covers.includes('w:切ります:group'));
  assert.deepEqual(it.skills, ['變化']);
});

test('不在 verbsTable 中的單字直接跳過，不得猜分類', () => {
  const items = [...generate([{ kana: 'ぜんぜんない', zh: 'x', lesson: 1 }], VERBS)];
  assert.equal(items.length, 0);
});
