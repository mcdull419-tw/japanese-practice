import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_SETTINGS, loadSettings } from '../../app/ui/settings.js';
import { SKILLS } from '../../app/core/concepts.js';

test('預設開啟全部題型與六類技能', () => {
  assert.deepEqual(DEFAULT_SETTINGS.engines, ['recall', 'transform', 'substitute', 'drill', 'cloze']);
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

// 練習Ａ／Ｂ 原本共用「代入題」一個開關，拆開後舊設定裡沒有 drill。
// 練習Ｂ 要跟著舊的代入題開關走，否則開著代入題的人會突然少掉練習Ｂ。
const stored = (obj) => ({ getItem: () => JSON.stringify(obj) });

test('拆開關前的舊設定：代入題開著，練習Ｂ 也開著', () => {
  const s = loadSettings(stored({ engines: ['recall', 'substitute'] }));
  assert.deepEqual(s.engines, ['recall', 'substitute', 'drill']);
});

test('拆開關前的舊設定：代入題關著，練習Ｂ 也關著', () => {
  const s = loadSettings(stored({ engines: ['recall', 'cloze'] }));
  assert.deepEqual(s.engines, ['recall', 'cloze']);
});

test('拆開關後只關練習Ｂ，重新載入不會被補回來', () => {
  const s = loadSettings(stored({ engines: ['recall', 'substitute'], knownEngines: ['recall', 'transform', 'substitute', 'drill', 'cloze'] }));
  assert.deepEqual(s.engines, ['recall', 'substitute']);
});
