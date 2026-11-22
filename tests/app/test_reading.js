import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buildLexicon } from '../../app/core/ruby.js';
import { matchesReading, buildInputLexicon } from '../../app/core/reading.js';
import { gradeAnswer } from '../../app/core/grading.js';

const lexJson = JSON.parse(readFileSync(new URL('../../data/ruby-lexicon.json', import.meta.url)));
const lex = buildLexicon(lexJson);
const inputLex = buildInputLexicon(
  [{ kanji: '私', kana: 'わたし' }, { kanji: '買います', kana: 'かいます' }],
  lex, Object.keys(lexJson.ambiguous));
const ok = (input, answer) => matchesReading(input, answer, lex, inputLex);

test('整句：答案的漢字詞寫成讀音也算對，可混寫', () => {
  const a = 'わたしは毎朝6じに起きます。';
  assert.ok(ok('わたしはまいあさ6じにおきます', a));
  assert.ok(ok('わたしは毎朝6じにおきます', a));
  assert.ok(ok('わたしは まいあさ ６じに 起きます。', a));
});

test('整句：答案寫假名、使用者寫漢字也算對', () => {
  assert.ok(ok('私は何も買いません', 'わたしは何もかいません。'));
  assert.ok(ok('わたしは毎朝6時に起きます', 'わたしは毎朝6じに起きます。'));
});

test('多讀音字依上下文：ドイツ人＝じん、会社の人＝ひと', () => {
  assert.ok(ok('わっとさんはどいつじんじゃありません', 'ワットさんは ドイツ人じゃ ありません。'));
  assert.ok(!ok('わっとさんはどいつひとじゃありません', 'ワットさんは ドイツ人じゃ ありません。'));
  assert.ok(ok('かいしゃのひとといきます', '会社の 人と 行きます。'));
  assert.ok(ok('なにをたべましたか', '何を 食べましたか。'));
  assert.ok(ok('なんじからですか', '何時からですか。'));
});

test('數字照打，量詞漢字／假名皆可；千分位逗號可省', () => {
  assert.ok(ok('9じはんから5じ45ふんまで', '9時半から 5時45分まで'));
  assert.ok(ok('このネクタイは13000円です', 'このネクタイは13,000えんです。'));
  assert.ok(ok('1回いきます', '1かい行きます'));
});

test('錯的仍然判錯：助詞、詞彙、讀音不對', () => {
  const a = 'わたしは毎朝6じに起きます。';
  assert.ok(!ok('わたしは毎朝6じを起きます', a));
  assert.ok(!ok('わたしは毎朝7じに起きます', a));
  assert.ok(!ok('わたしはまいばん6じにおきます', a));
  assert.ok(!ok('いつ行きますか。きねんの3月に行きます', 'いつ 行きますか。 来年の 3月に 行きます。'));
  assert.ok(!ok('', a));
});

test('strictKana（問讀音的題）不收漢字寫法', () => {
  const item = { answer: 'にほん', alternatives: [], strictKana: true };
  assert.equal(gradeAnswer('日本', item, 1, 1, false, { lex, inputLex }).correct, false);
  assert.equal(gradeAnswer('にほん', item, 1, 1, false, { lex, inputLex }).correct, true);
});

test('一般題：alternatives 也照讀音比對', () => {
  const item = { answer: 'あの人はだれですか。', alternatives: ['あの方はどなたですか。'] };
  assert.equal(gradeAnswer('あのかたはどなたですか', item, 1, 1, false, { lex, inputLex }).correct, true);
});

test('輸入端詞典：單字表的漢字段推得讀音；多讀音字不收', () => {
  const il = buildInputLexicon([
    { kanji: '私', kana: 'わたし' },
    { kanji: '買います', kana: 'かいます' },
    { kanji: 'お茶', kana: 'おちゃ' },
    { kanji: '人', kana: 'ひと' },
  ], new Map(), ['人']);
  assert.equal(il.get('私'), 'わたし');
  assert.equal(il.get('買'), 'か');
  assert.equal(il.get('茶'), 'ちゃ');
  assert.equal(il.has('人'), false);
});
