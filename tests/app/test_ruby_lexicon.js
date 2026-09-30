import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buildLexicon, annotateWithLexicon } from '../../app/core/ruby.js';

const lexJson = JSON.parse(readFileSync(new URL('../../data/ruby-lexicon.json', import.meta.url)));

function allLessons() {
  const out = [];
  for (let n = 1; n <= 15; n++) {
    out.push(JSON.parse(readFileSync(
      new URL(`../../data/lessons/${String(n).padStart(2, '0')}.json`, import.meta.url))));
  }
  return out;
}

test('auto 區的每一條都能從當前語料的標註回推得到（語料重抽即紅燈）', () => {
  const fromCorpus = new Map();
  for (const d of allLessons()) {
    for (const s of d.sentences || []) {
      for (const r of s.ruby || []) {
        if (!fromCorpus.has(r.base)) fromCorpus.set(r.base, new Set());
        fromCorpus.get(r.base).add(r.kana);
      }
    }
  }
  for (const [base, kana] of Object.entries(lexJson.auto)) {
    const readings = fromCorpus.get(base);
    assert.ok(readings, `詞典的 ${base} 已不存在於語料標註中`);
    assert.ok(readings.has(kana), `${base} 的讀音 ${kana} 已不存在於語料標註中`);
    assert.equal(readings.size, 1, `${base} 在語料中已出現多種讀音，應移出 auto 區`);
  }
});

test('多讀音字不得出現在 auto 區（會在題目上印出錯的讀音）', () => {
  for (const base of Object.keys(lexJson.ambiguous || {})) {
    assert.equal(lexJson.auto[base], undefined, `多讀音字 ${base} 不得自動加注`);
  }
});

test('詞典的 kana 全為假名，base 全含漢字', () => {
  const lex = buildLexicon(lexJson);
  for (const [base, kana] of lex) {
    assert.match(base, /[一-鿿]/, `${base} 不含漢字，不該進詞典`);
    assert.match(kana, /^[぀-ゟ゠-ヿー]+$/, `${base} 的讀音 ${kana} 不是純假名`);
  }
});

test('加注後移除 rt 必須還原成原文（絕不改動句子本身）', () => {
  const lex = buildLexicon(lexJson);
  for (const d of allLessons()) {
    for (const p of d.patterns || []) {
      const text = p.template || '';
      const back = annotateWithLexicon(text, lex)
        .map((t) => (t.t === 'ruby' ? t.base : t.s)).join('');
      assert.equal(back, text, `${p.id} 加注後無法還原`);
    }
  }
});
