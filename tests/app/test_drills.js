import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { generate } from '../../app/generators/drills.js';

const sample = {
  'L08-B2': {
    lesson: 8,
    source_ref: '第8課 練習Ｂ-2',
    model_cue: '山田さん・元気',
    model_answer: '山田さんは 元気じゃ ありません。',
    rows: [
      { cue: 'ミラーさん・忙しい', answer: 'ミラーさんは 忙しくないです。' },
      { cue: 'イーさん・暇', answer: 'イーさんは 暇じゃ ありません。' },
    ],
  },
  'L06-B2': {
    lesson: 6,
    source_ref: '第6課 練習Ｂ-2',
    model_cue: 'たばこを 吸いますか。（ はい ）',
    model_answer: 'はい、吸います。',
    ask: true,
    rows: [{ cue: 'お酒を 飲みますか。（ いいえ ）', answer: 'いいえ、飲みません。' }],
  },
};

test('每一列產生一題，答案取自人工書寫的那一列', () => {
  const items = [...generate(sample, new Map())];
  assert.equal(items.length, 3);
  const it = items[0];
  assert.equal(it.id, 'drill:L08-B2:0');
  assert.equal(it.engine, 'substitute');
  assert.equal(it.answer, 'ミラーさんは 忙しくないです。');
  assert.equal(it.lesson, 8);
  assert.equal(it.requires_lesson, 8);
  assert.equal(it.source_ref, '第8課 練習Ｂ-2');
});

test('題幹含範例與該列提示，但不含該列答案', () => {
  const it = [...generate(sample, new Map())][0];
  assert.ok(it.prompt.text.includes('山田さんは 元気じゃ ありません。'), '題幹須有範例答案');
  assert.ok(it.prompt.text.includes('ミラーさん・忙しい'), '題幹須有該列提示');
  assert.ok(!it.prompt.text.includes('忙しくないです'), '題幹不得洩漏答案');
});

test('ask 型的題幹不加「用這個提示造句」，提示語改為回答', () => {
  const it = [...generate(sample, new Map())].find((x) => x.id === 'drill:L06-B2:0');
  assert.ok(!it.prompt.text.includes('用這個提示造句'));
  assert.equal(it.prompt.hint, '照範例回答問題');
  assert.equal(it.answer, 'いいえ、飲みません。');
});

test('概念對應得到時用概念，對應不到時退回以該則 id 當概念', () => {
  const withConcept = [...generate(sample, new Map([['L08-B2', ['g:adj_negative']]]))][0];
  assert.deepEqual(withConcept.covers, ['g:adj_negative']);
  assert.deepEqual(withConcept.skills, ['句型']);

  const without = [...generate(sample, new Map())][0];
  assert.deepEqual(without.covers, ['g:L08-B2']);
  assert.deepEqual(without.skills, ['句型']);
});

test('id 決定性：重跑兩次完全一致', () => {
  const a = [...generate(sample, new Map())].map((x) => x.id);
  const b = [...generate(sample, new Map())].map((x) => x.id);
  assert.deepEqual(a, b);
});

test('真實題庫產出 200 題以上，且每題答案非空、id 不重複', () => {
  const drills = JSON.parse(readFileSync(new URL('../../data/drills.json', import.meta.url)));
  const items = [...generate(drills, new Map())];
  assert.ok(items.length >= 200, `只有 ${items.length} 題`);
  const ids = new Set(items.map((x) => x.id));
  assert.equal(ids.size, items.length, 'id 有重複');
  for (const it of items) {
    assert.ok(it.answer.length > 0, `${it.id} 答案為空`);
    assert.ok(it.prompt.text.includes(it.answer) === false, `${it.id} 題幹洩漏答案`);
  }
});

// 見 test_substitute.js 同名測試。ask 型只有「例：」一個標籤。
test('宣告的中文標籤都真的出現在題幹裡', () => {
  for (const it of [...generate(sample, null)]) {
    assert.ok((it.prompt.zhParts || []).length > 0, `${it.id} 沒有宣告中文標籤`);
    for (const lit of it.prompt.zhParts) {
      assert.ok(it.prompt.text.includes(lit), `${it.id} 宣告了「${lit}」但題幹裡沒有`);
    }
  }
});
