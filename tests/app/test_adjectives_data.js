import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { conjugateAdj } from '../../app/lang/adjective.js';
import { splitForms } from '../../app/lang/altforms.js';

const adjectives = JSON.parse(readFileSync(new URL('../../data/adjectives.json', import.meta.url)));

function allVocab() {
  const out = [];
  for (let n = 1; n <= 15; n++) {
    const d = JSON.parse(readFileSync(new URL(`../../data/lessons/${String(n).padStart(2, '0')}.json`, import.meta.url)));
    for (const v of d.vocab || []) out.push({ ...v, lesson: n });
  }
  return out;
}

test('每個鍵都在課本單字表中找得到（去掉［な］後比對）', () => {
  const cites = new Set();
  for (const v of allVocab()) {
    // 課本有三種會讓字面比對落空的寫法，都要一併收進可接受的引用形：
    //   ［な］ 標記（静か［な］）、括號異寫（いい  （よい））、
    //   並列寫法（暑い、熱い——鍵取第一個寫法，與 transform.js 一致）。
    const strip = (s) => (s || '').replace('［な］', '').trim();
    for (const raw of [v.kanji, v.kana]) {
      const t = strip(raw);
      if (!t) continue;
      cites.add(t);
      cites.add(t.split('（')[0].trim());
      for (const f of splitForms(t)) cites.add(f);
    }
  }
  for (const key of Object.keys(adjectives)) {
    assert.ok(cites.has(key), `adjectives.json 的「${key}」在課本單字表中不存在`);
  }
});

test('每筆欄位齊備且 type 合法', () => {
  for (const [key, info] of Object.entries(adjectives)) {
    assert.ok(['i', 'na'].includes(info.type), `${key} 的 type 非法：${info.type}`);
    assert.equal(typeof info.kana, 'string', `${key} 缺 kana`);
    assert.ok(info.kana.length > 0, `${key} 的 kana 為空`);
    assert.equal(typeof info.lesson, 'number', `${key} 缺 lesson`);
    assert.ok(info.lesson >= 1 && info.lesson <= 15, `${key} 的 lesson 超出 1~15：${info.lesson}`);
    assert.ok(!key.includes('［'), `${key} 的鍵未去除［な］標記`);
  }
});

test('每筆都能實際變化，不拋錯', () => {
  for (const [key, info] of Object.entries(adjectives)) {
    for (const form of ['plain', 'neg', 'past', 'pastneg']) {
      assert.doesNotThrow(() => conjugateAdj(key, info.type, form), `${key} 的 ${form} 變化失敗`);
      assert.doesNotThrow(() => conjugateAdj(info.kana, info.type, form), `${key} 的假名形 ${form} 變化失敗`);
    }
  }
});

test('形容詞數量在合理範圍（1~15課約 40~60 筆）', () => {
  const n = Object.keys(adjectives).length;
  assert.ok(n >= 35 && n <= 70, `形容詞筆數 ${n} 不在預期範圍，檢查是否漏收或誤收`);
});
