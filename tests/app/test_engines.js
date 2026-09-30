import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync } from 'node:fs';
import { engineFor } from '../../app/engines/index.js';
import * as text from '../../app/engines/text.js';
import * as recall from '../../app/engines/recall.js';

const item = (over = {}) => ({
  id: 'x', engine: 'recall', prompt: { type: 'text', text: '書', hint: '寫出讀音' },
  answer: 'かく', covers: [], skills: [], ...over,
});

test('engineFor 依 item.engine 分派', () => {
  assert.equal(engineFor(item({ engine: 'recall' })), recall);
  assert.equal(engineFor(item({ engine: 'cloze' })).ENGINE, 'cloze');
});

test('engineFor 遇到未知引擎退回打字作答，不拋錯', () => {
  assert.equal(engineFor(item({ engine: 'mystery' })), text);
  assert.equal(engineFor(null), text);
});

test('每個引擎都 export render 與 ENGINE', async () => {
  for (const name of ['text', 'recall', 'transform', 'substitute', 'cloze']) {
    const mod = await import(`../../app/engines/${name}.js`);
    assert.equal(typeof mod.render, 'function', `${name} 缺 render`);
    assert.equal(typeof mod.ENGINE, 'string', `${name} 缺 ENGINE`);
  }
});

test('引擎不得 import 其他引擎（規格 §6.1：引擎彼此不互相依賴）', () => {
  for (const f of readdirSync(new URL('../../app/engines/', import.meta.url))) {
    if (f === 'index.js') continue;
    const src = readFileSync(new URL(`../../app/engines/${f}`, import.meta.url), 'utf8');
    const bad = [...src.matchAll(/from '\.\/(\w+)\.js'/g)].map((m) => m[1])
      .filter((n) => n !== 'text');
    assert.deepEqual(bad, [], `${f} 不得 import 其他引擎：${bad}`);
  }
});

test('引擎不得自行比對答案（判斷邏輯一律走 core/grading.js）', () => {
  for (const f of readdirSync(new URL('../../app/engines/', import.meta.url))) {
    const src = readFileSync(new URL(`../../app/engines/${f}`, import.meta.url), 'utf8');
    assert.ok(!/isCorrect|normalizeAnswer|gradeAnswer/.test(src),
      `${f} 自行做了判斷，違反規格 §11 的分層`);
  }
});

test('promptHtml：聽力模式不洩漏題幹文字', () => {
  const html = text.promptHtml(item({ prompt: { text: '手紙を 書きます。' } }), { listening: true });
  assert.ok(!html.includes('手紙'), '聽力模式的題幹不得出現文字');
});

test('promptHtml：有 ruby token 時以 ruby 渲染，hideRt 時不含讀音', () => {
  const it = item({ prompt: { text: '手紙' } });
  const tokens = [{ t: 'ruby', base: '手紙', kana: 'てがみ' }];
  assert.equal(text.promptHtml(it, { rubyTokens: tokens }),
    '<ruby>手紙<rt>てがみ</rt></ruby>');
  assert.equal(text.promptHtml(it, { rubyTokens: tokens, hideRt: true }), '手紙');
});

test('promptHtml：沒有 ruby token 時換行轉成 br', () => {
  const it = item({ prompt: { text: '例：あ\n用這些詞造句：い' } });
  assert.ok(text.promptHtml(it, {}).includes('<br>'));
});
