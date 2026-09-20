import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const verbs = JSON.parse(await readFile('data/verbs.json', 'utf8'));
const lessons = await Promise.all(
  [...Array(15)].map((_, i) =>
    readFile(`data/lessons/${String(i + 1).padStart(2, '0')}.json`, 'utf8').then(JSON.parse))
);

// 鍵 = 引用形（kanji || kana）。這樣「起きます」(II) 與「置きます」(I)
// 這種同假名不同動詞才不會互相覆蓋——見下方「引用形為鍵」測試。
function keyOf(v) {
  return v.kanji || v.kana;
}

test('涵蓋語料中所有 ます 結尾的單字（排除非單一動詞者）', () => {
  const EXCLUDE = new Set(['しって  います', 'すんで  います', 'いらっしゃいます います']);
  const missing = [];
  for (const d of lessons) {
    for (const v of d.vocab) {
      const form = v.kanji || v.kana || '';
      if (!form.endsWith('ます')) continue;
      if (EXCLUDE.has(v.kana)) continue;
      if (!verbs[keyOf(v)]) missing.push(`L${d.lesson} ${keyOf(v)}`);
    }
  }
  assert.deepEqual(missing, [], `未收錄: ${missing.join(', ')}`);
});

test('與課本自身的 group 標記完全一致', () => {
  const conflicts = [];
  for (const d of lessons) {
    for (const v of d.vocab) {
      if (!v.group || !verbs[keyOf(v)]) continue;
      if (verbs[keyOf(v)].group !== v.group) {
        conflicts.push(`${keyOf(v)}: 表=${verbs[keyOf(v)].group} 課本=${v.group}`);
      }
    }
  }
  assert.deepEqual(conflicts, [], conflicts.join('; '));
});

test('課本未標註但已知的關鍵分類正確', () => {
  assert.equal(verbs['貸します'].group, 'I');      // 貸す：非 する 複合
  assert.equal(verbs['帰ります'].group, 'I');      // 帰る：外形像 II 類的 I 類
  assert.equal(verbs['借ります'].group, 'II');     // 借りる：i 段但為 II 類
  assert.equal(verbs['切ります'].group, 'I');      // 切る
  assert.equal(verbs['入ります'].group, 'I');      // 入る：同 帰る
  assert.equal(verbs['起きます'].group, 'II');     // 起きる
  assert.equal(verbs['置きます'].group, 'I');      // 置く：與 起きます 同假名，課本第15課明標 I
  assert.equal(verbs['食べます'].group, 'II');     // 食べる
  assert.equal(verbs['勉強します'].group, 'III');
  assert.equal(verbs['来ます'].group, 'III');      // 来る（vocab.kanji="来ます"，鍵非「きます」）
  assert.equal(verbs['します'].group, 'III');      // する（無漢字，鍵仍為假名）
});

test('引用形為鍵：同假名不同動詞不互相覆蓋', () => {
  assert.notEqual(verbs['起きます'].group, verbs['置きます'].group);
  assert.equal(verbs['起きます'].kana, verbs['置きます'].kana); // 假名相同（おきます）
});

test('鍵不含空白（否則 conjugate 會切錯語幹並靜默產生錯誤答案）', () => {
  for (const k of Object.keys(verbs)) {
    assert.equal(/[\s　]/.test(k), false, `鍵含空白: ${JSON.stringify(k)}`);
  }
});

test('每筆都有 group／dict／kana，group 值合法', () => {
  for (const [k, v] of Object.entries(verbs)) {
    assert.ok(['I', 'II', 'III'].includes(v.group), `${k} group 非法: ${v.group}`);
    assert.ok(typeof v.dict === 'string' && v.dict.length > 0, `${k} 缺 dict`);
    assert.ok(typeof v.kana === 'string' && v.kana.endsWith('ます'), `${k} 缺合法 kana`);
  }
});
