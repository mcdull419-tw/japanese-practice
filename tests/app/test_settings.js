import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_SETTINGS, loadSettings } from '../../app/ui/settings.js';
import { SKILLS } from '../../app/core/concepts.js';

test('預設開啟四個引擎與六類技能', () => {
  assert.deepEqual(DEFAULT_SETTINGS.engines, ['recall', 'transform', 'substitute', 'cloze']);
  assert.deepEqual(DEFAULT_SETTINGS.skills, SKILLS);
});

test('舊版設定沒有 skills 欄位時補上預設值（不讓既有使用者的題目消失）', () => {
  const storage = { getItem: () => JSON.stringify({ minLesson: 1, maxLesson: 15, engines: ['recall'], sessionSize: 20 }) };
  const s = loadSettings(storage);
  assert.deepEqual(s.skills, SKILLS);
  assert.deepEqual(s.engines, ['recall'], '既有欄位不得被預設值蓋掉');
});

test('儲存被封鎖時回預設值', () => {
  const storage = { getItem: () => { throw new Error('blocked'); } };
  assert.deepEqual(loadSettings(storage), DEFAULT_SETTINGS);
});
