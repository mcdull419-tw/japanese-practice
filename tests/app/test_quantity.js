import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../app/generators/quantity.js';

const items = [...generate()];
const byId = new Map(items.map((it) => [it.id, it]));

test('時刻題：4時 → よじ', () => {
  const it = byId.get('qty:hour:4');
  assert.ok(it, '應有 qty:hour:4');
  assert.equal(it.engine, 'recall');
  assert.equal(it.prompt.text, '4時');
  assert.equal(it.answer, 'よじ');
  assert.deepEqual(it.covers, ['n:time:hour']);
  assert.deepEqual(it.skills, ['數量']);
  assert.equal(it.requires_lesson, 4);
});

test('日期題：20日 → はつか', () => {
  const it = byId.get('qty:day:20');
  assert.ok(it);
  assert.equal(it.answer, 'はつか');
  assert.deepEqual(it.covers, ['n:date:day']);
  assert.equal(it.requires_lesson, 5);
});

test('量詞題：3本 → さんぼん', () => {
  const it = byId.get('qty:c:hon:3');
  assert.ok(it);
  assert.equal(it.prompt.text, '3本');
  assert.equal(it.answer, 'さんぼん');
  assert.deepEqual(it.covers, ['c:hon']);
  assert.equal(it.requires_lesson, 11);
});

test('樓層與次數雖同為かい，但各自獨立成題', () => {
  assert.equal(byId.get('qty:c:kai_floor:3').answer, 'さんがい');
  assert.equal(byId.get('qty:c:kai_times:3').answer, 'さんかい');
  assert.notEqual(byId.get('qty:c:kai_floor:3').covers[0], byId.get('qty:c:kai_times:3').covers[0]);
});

test('全部 id 唯一且決定性（重跑兩次結果相同）', () => {
  const ids = items.map((it) => it.id);
  assert.equal(new Set(ids).size, ids.length, '不得有重複 id');
  const again = [...generate()].map((it) => it.id);
  assert.deepEqual(again, ids, '同一份規則重跑必須得到同一組 id');
});

test('每題欄位齊備', () => {
  for (const it of items) {
    assert.equal(typeof it.id, 'string');
    assert.equal(it.engine, 'recall');
    assert.ok(Array.isArray(it.covers) && it.covers.length > 0, `${it.id} 缺 covers`);
    assert.ok(it.answer.length > 0, `${it.id} 缺答案`);
    assert.ok(it.source_ref.length > 0, `${it.id} 缺出處`);
    assert.ok(it.requires_lesson >= 1 && it.requires_lesson <= 15, `${it.id} 的 requires_lesson 異常`);
    assert.ok(it.lesson >= 1 && it.lesson <= 15, `${it.id} 的 lesson 異常`);
  }
});

test('題數在預期範圍', () => {
  // 時12 ＋ 分14 ＋ 日31 ＋ 月12 ＝ 69，量詞 12 種 × 10 ＝ 120
  assert.ok(items.length >= 150 && items.length <= 220, `題數 ${items.length} 不如預期`);
});
