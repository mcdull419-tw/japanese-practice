import { test } from 'node:test';
import assert from 'node:assert/strict';
import { annotateWithMarks } from '../../app/core/ruby.js';

test('依標註切出 text 與 ruby 交錯的 token', () => {
  const text = 'わたしは  ワープロで  手紙を  書きます。';
  const marks = [
    { at: 13, base: '手紙', kana: 'てがみ' },
    { at: 18, base: '書', kana: 'か' },
  ];
  assert.deepEqual(annotateWithMarks(text, marks), [
    { t: 'text', s: 'わたしは  ワープロで  ' },
    { t: 'ruby', base: '手紙', kana: 'てがみ' },
    { t: 'text', s: 'を  ' },
    { t: 'ruby', base: '書', kana: 'か' },
    { t: 'text', s: 'きます。' },
  ]);
});

test('沒有標註時回傳單一 text token', () => {
  assert.deepEqual(annotateWithMarks('これは 本です。', []), [{ t: 'text', s: 'これは 本です。' }]);
});

test('標註位置對不上文字時跳過該筆，不拋錯也不錯位', () => {
  const marks = [{ at: 3, base: '手紙', kana: 'てがみ' }]; // at 指到的不是 手紙
  assert.deepEqual(annotateWithMarks('これは 本です。', marks), [{ t: 'text', s: 'これは 本です。' }]);
});

test('標註未依 at 排序時仍正確切詞', () => {
  const marks = [
    { at: 18, base: '書', kana: 'か' },
    { at: 13, base: '手紙', kana: 'てがみ' },
  ];
  const tokens = annotateWithMarks('わたしは  ワープロで  手紙を  書きます。', marks);
  assert.deepEqual(tokens.filter((t) => t.t === 'ruby').map((t) => t.base), ['手紙', '書']);
});

test('空字串與非字串輸入回傳空陣列', () => {
  assert.deepEqual(annotateWithMarks('', []), []);
  assert.deepEqual(annotateWithMarks(null, []), []);
});

// ── 詞典最長匹配（練習Ａ／Ｂ 沒有課本標註，只能靠詞典）──────────────
import { buildLexicon, annotateWithLexicon } from '../../app/core/ruby.js';

test('buildLexicon 以 manual 覆蓋 auto', () => {
  const lex = buildLexicon({ auto: { 何: 'なに', 手紙: 'てがみ' }, manual: { 何: 'なん' } });
  assert.equal(lex.get('何'), 'なん');
  assert.equal(lex.get('手紙'), 'てがみ');
});

test('buildLexicon 容忍缺少 auto／manual 區', () => {
  assert.equal(buildLexicon({}).size, 0);
  assert.equal(buildLexicon(null).size, 0);
});

test('最長匹配優先：日本人 不可被切成 日本 ＋ 人', () => {
  const lex = buildLexicon({ auto: { 日本: 'にほん', 日本人: 'にほんじん' } });
  const tokens = annotateWithLexicon('日本人は はしで 食べます。', lex);
  assert.deepEqual(tokens[0], { t: 'ruby', base: '日本人', kana: 'にほんじん' });
});

test('詞典沒有的漢字原樣留在 text token，不加注', () => {
  const lex = buildLexicon({ auto: { 手紙: 'てがみ' } });
  assert.deepEqual(annotateWithLexicon('電気を 消します。', lex), [
    { t: 'text', s: '電気を 消します。' },
  ]);
});

test('只在漢字段上匹配，假名與標點不動', () => {
  const lex = buildLexicon({ auto: { 書: 'か' } });
  assert.deepEqual(annotateWithLexicon('手紙を 書きます。', lex), [
    { t: 'text', s: '手紙を ' },
    { t: 'ruby', base: '書', kana: 'か' },
    { t: 'text', s: 'きます。' },
  ]);
});

test('同一段漢字中匹配不到的字不會吞掉後面匹配得到的字', () => {
  const lex = buildLexicon({ auto: { 紙: 'かみ' } });
  assert.deepEqual(annotateWithLexicon('手紙', lex), [
    { t: 'text', s: '手' },
    { t: 'ruby', base: '紙', kana: 'かみ' },
  ]);
});

test('相鄰的 text token 會被合併，不產生碎片', () => {
  const lex = buildLexicon({ auto: {} });
  assert.deepEqual(annotateWithLexicon('あ亜い', lex), [{ t: 'text', s: 'あ亜い' }]);
});
