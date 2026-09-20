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
