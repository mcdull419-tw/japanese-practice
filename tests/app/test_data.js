import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { loadLessons, buildIndex } from '../../app/core/data.js';

const fsLoader = async (n) =>
  JSON.parse(await readFile(`data/lessons/${String(n).padStart(2, '0')}.json`, 'utf8'));

test('loadLessons 載入指定課次', async () => {
  const m = await loadLessons([7], fsLoader);
  assert.equal(m.size, 1);
  assert.equal(m.get(7).lesson, 7);
  assert.equal(m.get(7).vocab.length, 48);
});

test('buildIndex 攤平並標註課次', async () => {
  const m = await loadLessons([7, 14], fsLoader);
  const idx = buildIndex(m);
  const kiri = idx.vocab.find((v) => v.kana === 'きります');
  assert.equal(kiri.lesson, 7);
  assert.equal(kiri.kanji, '切ります');
  const tsuke = idx.vocab.find((v) => v.kana === 'つけます');
  assert.equal(tsuke.lesson, 14);
  assert.equal(tsuke.group, 'II');
});

test('buildIndex 涵蓋全 15 課的實際總數', async () => {
  const all = await loadLessons([...Array(15)].map((_, i) => i + 1), fsLoader);
  const idx = buildIndex(all);
  assert.equal(idx.vocab.length, 749);
  assert.equal(idx.sentences.length, 430);
});

test('buildIndex 攤平 patterns 與 drills 並帶上課次', () => {
  const lessons = new Map([
    [7, {
      vocab: [], sentences: [],
      patterns: [{ id: 'L07-A1', template: '{S}は{T}で ごはんを 食べます。', slots: { S: ['日本人'], T: ['はし'] }, rows: [[0, 0]], requires_lesson: 7 }],
      drills: [{ id: 'L07-B1', items: ['手紙を 書きます'], model_answer: 'はしで ごはんを 食べます。', model_cue: 'ごはんを 食べます' }],
    }],
  ]);
  const idx = buildIndex(lessons);
  assert.equal(idx.patterns.length, 1);
  assert.equal(idx.patterns[0].id, 'L07-A1');
  assert.equal(idx.patterns[0].lesson, 7);
  assert.equal(idx.patterns[0].template, '{S}は{T}で ごはんを 食べます。');
  assert.equal(idx.drills.length, 1);
  assert.equal(idx.drills[0].lesson, 7);
  assert.equal(idx.drills[0].model_answer, 'はしで ごはんを 食べます。');
});

test('buildIndex 對缺少 patterns／drills 的課次不炸', () => {
  const idx = buildIndex(new Map([[1, { vocab: [], sentences: [] }]]));
  assert.deepEqual(idx.patterns, []);
  assert.deepEqual(idx.drills, []);
});
