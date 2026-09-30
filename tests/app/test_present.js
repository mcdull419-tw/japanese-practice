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

/**
 * 中文和日文共用 CJK 統一漢字區，詞典的最長匹配分不出來：中文的「起」會被配上
 * 日文讀音 お（來自 起きます）。題幹語言只有產生器知道，因此由題目自己宣告，
 * 呈現端據此跳過——不能在 ruby.js 裡猜，那支是純切詞函式。
 */
test('題幹標為中文時不加振假名（中文字會被配上日文讀音）', () => {
  const item = { id: 'recall:てがみ:zh2jp', covers: [], prompt: { text: '手紙', lang: 'zh' } };
  const opts = presentOptsFor(item, { lex, sentenceMarks: new Map() });
  assert.deepEqual(opts.rubyTokens, [{ t: 'text', s: '手紙' }],
    '中文題幹必須原樣輸出，不得出現 ruby token');
});

test('沒有標語言的題幹照舊加振假名（既有題型不受影響）', () => {
  const item = { id: 'x', covers: [], prompt: { text: '手紙' } };
  const opts = presentOptsFor(item, { lex, sentenceMarks: new Map() });
  assert.deepEqual(opts.rubyTokens, [{ t: 'ruby', base: '手紙', kana: 'てがみ' }]);
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

test('題目宣告 hideRuby 時藏住讀音，即使 covers 沒有 :reading 後綴', () => {
  const item = { id: 'qty:c:本:1', covers: ['c:本'], prompt: { text: '1本', hideRuby: true } };
  const opts = presentOptsFor(item, { lex, sentenceMarks: new Map() });
  assert.equal(opts.hideRt, true, '問唸法的題目不得顯示讀音');
});

/**
 * 混排題幹（練習Ａ／Ｂ）：中文標籤與日文例句同在一個字串裡。以字串而非位置索引
 * 標示中文段落——這個專案已經吃過偏移的虧（見上方挖空題位移的測試）。
 */
test('混排題幹只標註日文段落，中文標籤原樣輸出', () => {
  // 「例」必須在詞典裡，否則這條測試會因為查不到而假性通過——實際語料中
  // 例→れい 正是唯一被誤標的字。
  const mixedLex = buildLexicon({ auto: { 手紙: 'てがみ', 書: 'か', 例: 'れい' } });
  const item = {
    id: 'drill:x:0', covers: [],
    prompt: { text: '例：手紙を書きます\n用這個提示造句：手紙', zhParts: ['例：', '用這個提示造句：'] },
  };
  const opts = presentOptsFor(item, { lex: mixedLex, sentenceMarks: new Map() });
  const rubies = opts.rubyTokens.filter((t) => t.t === 'ruby').map((t) => t.base);
  assert.deepEqual(rubies, ['手紙', '書', '手紙'], '日文段落必須保有振假名');
  const flat = opts.rubyTokens.map((t) => (t.t === 'ruby' ? t.base : t.s)).join('');
  assert.equal(flat, '例：手紙を書きます\n用這個提示造句：手紙', '拼回去必須與原文一字不差');
});
