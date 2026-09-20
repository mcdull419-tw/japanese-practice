import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const verbs = JSON.parse(await readFile('data/verbs.json', 'utf8'));
const lessons = await Promise.all(
  [...Array(15)].map((_, i) =>
    readFile(`data/lessons/${String(i + 1).padStart(2, '0')}.json`, 'utf8').then(JSON.parse))
);

test('涵蓋語料中所有 ます 結尾的單字（排除非單一動詞者）', () => {
  const EXCLUDE = new Set(['しって  います', 'すんで  います', 'いらっしゃいます います']);
  const missing = [];
  for (const d of lessons) {
    for (const v of d.vocab) {
      const form = v.kanji || v.kana || '';
      if (!form.endsWith('ます')) continue;
      if (EXCLUDE.has(v.kana)) continue;
      if (!verbs[v.kana]) missing.push(`L${d.lesson} ${v.kana}`);
    }
  }
  assert.deepEqual(missing, [], `未收錄: ${missing.join(', ')}`);
});

test('與課本自身的 group 標記完全一致', () => {
  const conflicts = [];
  for (const d of lessons) {
    for (const v of d.vocab) {
      if (!v.group || !verbs[v.kana]) continue;
      if (verbs[v.kana].group !== v.group) {
        conflicts.push(`${v.kana}: 表=${verbs[v.kana].group} 課本=${v.group}`);
      }
    }
  }
  assert.deepEqual(conflicts, [], conflicts.join('; '));
});

test('課本未標註但已知的關鍵分類正確', () => {
  assert.equal(verbs['かします'].group, 'I');      // 貸す：非 する 複合
  assert.equal(verbs['かえります'].group, 'I');    // 帰る：外形像 II 類的 I 類
  assert.equal(verbs['かります'].group, 'II');     // 借りる：i 段但為 II 類
  assert.equal(verbs['きります'].group, 'I');      // 切る
  assert.equal(verbs['はいります'].group, 'I');    // 入る：同 帰る
  // おきます 是同形異義詞衝突：起きる(II，L4 未標註) 與 置く(I，L15 課本明標)
  // 共用同一假名鍵。課本第 15 課已明確標註 group="I"（給 置きます），
  // 依專案規則「課本標記優先」，此鍵採 I／置く。這是本表 schema（鍵=kana）
  // 無法同時代表兩個同形動詞的已知限制，見 commit message 說明。
  assert.equal(verbs['おきます'].group, 'I');      // 置く（與 起きる 同形，課本標記優先）
  assert.equal(verbs['たべます'].group, 'II');     // 食べる
  assert.equal(verbs['べんきょうします'].group, 'III');
  assert.equal(verbs['きます'].group, 'III');      // 来る
  assert.equal(verbs['します'].group, 'III');      // する
});

test('鍵不含空白（否則 conjugate 會切錯語幹並靜默產生錯誤答案）', () => {
  for (const k of Object.keys(verbs)) {
    assert.equal(/[\s　]/.test(k), false, `鍵含空白: ${JSON.stringify(k)}`);
  }
});

test('每筆都有 group 與 dict，group 值合法', () => {
  for (const [k, v] of Object.entries(verbs)) {
    assert.ok(['I', 'II', 'III'].includes(v.group), `${k} group 非法: ${v.group}`);
    assert.ok(typeof v.dict === 'string' && v.dict.length > 0, `${k} 缺 dict`);
  }
});
