import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../app/generators/transform.js';

const V = [
  { kana: 'おくります', kanji: '送ります', zh: '寄送', lesson: 7, no: 2 },
  { kana: 'たべます', kanji: '食べます', zh: '吃', lesson: 6, no: 1 },
  { kana: 'きります', kanji: '切ります', zh: '剪，切', lesson: 7, no: 1 },
  { kana: 'あげます', kanji: null, zh: '給，送', lesson: 7, no: 3 },
];
const VERBS = {
  送ります: { group: 'I', dict: '送る', kana: 'おくります' },
  食べます: { group: 'II', dict: '食べる', kana: 'たべます' },
  切ります: { group: 'I', dict: '切る', kana: 'きります' },
  あげます: { group: 'II', dict: 'あげる', kana: 'あげます' },
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

test('て形題以漢字出題，答案為漢字形，假名形列入 alternatives（修正 D）', () => {
  const it = [...generate(V, VERBS)].find((i) => i.id === 'conj:送ります:masu2te');
  assert.equal(it.prompt.text, '送ります');
  assert.equal(it.prompt.hint, 'て形');
  assert.equal(it.answer, '送って');
  assert.ok(it.alternatives.includes('おくって'));
  assert.equal(it.lesson, 7, '單字出自第 7 課');
  assert.equal(it.requires_lesson, 14, 'て形第 14 課才教');
});

test('時態題的 requires_lesson 為單字課次（ます形第 4 課已教），答案為漢字形', () => {
  const it = [...generate(V, VERBS)].find((i) => i.id === 'conj:食べます:masu2mashita');
  assert.equal(it.answer, '食べました');
  assert.ok(it.alternatives.includes('たべました'));
  assert.equal(it.requires_lesson, 6);
});

test('covers 含變化規則與該動詞的分類，skills 為「變化」', () => {
  const it = [...generate(V, VERBS)].find((i) => i.id === 'conj:切ります:masu2te');
  assert.equal(it.answer, '切って');
  assert.ok(it.alternatives.includes('きって'));
  assert.ok(it.covers.includes('r:te:groupI'));
  assert.ok(it.covers.includes('w:切ります:group'));
  assert.deepEqual(it.skills, ['變化']);
});

test('沒有漢字形的動詞維持假名出題，alternatives 為空（修正 D 的例外）', () => {
  const it = [...generate(V, VERBS)].find((i) => i.id === 'conj:あげます:masu2te');
  assert.equal(it.prompt.text, 'あげます');
  assert.equal(it.answer, 'あげて');
  assert.deepEqual(it.alternatives, []);
});

test('hint 不含語尾字樣，不得洩漏答案（修正 E）', () => {
  for (const it of generate(V, VERBS)) {
    assert.equal(/ませんでした|ました|ません/.test(it.prompt.hint), false,
      `hint 洩漏答案語尾: ${JSON.stringify(it.prompt.hint)}`);
  }
});

const V_MULTI = [
  { kana: 'つくります', kanji: '作ります、造ります', zh: '做，製造', lesson: 15, no: 5 },
];
const VERBS_MULTI = { 作ります: { group: 'I', dict: '作る', kana: 'つくります' } };

test('漢字欄含分隔符時取第一個寫法為引用形出題，其餘寫法與假名形都算對（修正 C／D）', () => {
  const it = [...generate(V_MULTI, VERBS_MULTI)].find((i) => i.id === 'conj:作ります:masu2te');
  assert.ok(it, '應能用第一個寫法「作ります」查到 verbsTable');
  assert.equal(it.prompt.text, '作ります');
  assert.equal(it.answer, '作って');
  assert.ok(it.alternatives.includes('つくって'), '假名形也要算對');
  assert.ok(it.alternatives.includes('造って'), '課本另列的寫法也要算對');
});

test('不在 verbsTable 中的單字直接跳過，不得猜分類', () => {
  const items = [...generate([{ kana: 'ぜんぜんない', zh: 'x', lesson: 1 }], VERBS)];
  assert.equal(items.length, 0);
});
