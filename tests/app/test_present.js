import { test } from 'node:test';
import assert from 'node:assert/strict';
import { presentOptsFor } from '../../app/ui/present.js';
import { buildLexicon } from '../../app/core/ruby.js';

const lex = buildLexicon({ auto: { 手紙: 'てがみ', 書: 'か' } });

test('考讀音的題型隱藏讀音（covers 含 :reading）', () => {
  const item = { id: 'recall:かく:kanji2kana', covers: ['w:書きます:reading'], prompt: { text: '書きます' } };
  const opts = presentOptsFor(item, { lex, sentenceMarks: new Map() });
  assert.equal(opts.hideRt, true);
});

test('其他題型一律顯示讀音', () => {
  const item = { id: 'recall:かく:zh2jp', covers: ['w:書きます'], prompt: { text: '手紙' } };
  const opts = presentOptsFor(item, { lex, sentenceMarks: new Map() });
  assert.equal(opts.hideRt, false);
  assert.deepEqual(opts.rubyTokens, [{ t: 'ruby', base: '手紙', kana: 'てがみ' }]);
});

test('題目對應得到課本句子時，優先用課本的精確標註', () => {
  const marks = new Map([['L07-文型-1', [{ at: 0, base: '手紙', kana: 'おてがみ' }]]]);
  const item = {
    id: 'cloze:L07-文型-1:3', covers: ['p:wo:object'],
    prompt: { text: '手紙を 書きます。' }, source_id: 'L07-文型-1',
  };
  const opts = presentOptsFor(item, { lex, sentenceMarks: marks });
  // 詞典會給 てがみ，課本標註給 おてがみ——必須以課本為準
  assert.equal(opts.rubyTokens[0].kana, 'おてがみ');
});

test('題幹無漢字時回傳單一 text token', () => {
  const item = { id: 'x', covers: [], prompt: { text: 'これは なんですか。' } };
  const opts = presentOptsFor(item, { lex, sentenceMarks: new Map() });
  assert.deepEqual(opts.rubyTokens, [{ t: 'text', s: 'これは なんですか。' }]);
});

test('挖空題的題幹與原句不同時（已挖掉助詞），標註位置對不上就退回詞典', () => {
  // 原句「手紙を 書きます。」被挖掉 を 之後位移，課本標註的 at 會對不上。
  const marks = new Map([['L07-文型-1', [{ at: 99, base: '書', kana: 'か' }]]]);
  const item = {
    id: 'cloze:L07-文型-1:3', covers: ['p:wo:object'],
    prompt: { text: '手紙＿ 書きます。' }, source_id: 'L07-文型-1',
  };
  const opts = presentOptsFor(item, { lex, sentenceMarks: marks });
  const bases = opts.rubyTokens.filter((t) => t.t === 'ruby').map((t) => t.base);
  assert.deepEqual(bases, ['手紙', '書'], '對不上的標註不該讓整句失去振假名');
});
