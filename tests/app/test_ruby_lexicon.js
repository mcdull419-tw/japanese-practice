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

// ── 覆蓋率（規格 §13 決定 9：人工補足到接近全覆蓋）────────────────
const KANJI_RUN = /[\u4e00-\u9fff]+/g;

function pdTexts() {
  const texts = [];
  for (const d of allLessons()) {
    for (const p of d.patterns || []) {
      texts.push(p.template || '');
      for (const vals of Object.values(p.slots || {})) {
        for (const v of vals) if (typeof v === 'string') texts.push(v);
      }
    }
    for (const dr of d.drills || []) {
      texts.push(dr.model_answer || '', dr.model_cue || '');
      for (const it of dr.items || []) if (typeof it === 'string') texts.push(it);
    }
  }
  return texts;
}

test('練習Ａ／Ｂ 文字的漢字覆蓋率達 97% 以上', () => {
  const lex = buildLexicon(lexJson);
  const ambiguous = new Set(Object.keys(lexJson.ambiguous || {}));
  let covered = 0, total = 0;
  const missing = new Map();
  for (const text of pdTexts()) {
    for (const token of annotateWithLexicon(text, lex)) {
      if (token.t === 'ruby') { covered += token.base.length; total += token.base.length; continue; }
      for (const run of token.s.match(KANJI_RUN) || []) {
        total += run.length;
        for (const ch of run) {
          // 多讀音字是「刻意不加注」，不算進缺口（規格 §13 決定 9）
          if (ambiguous.has(ch)) covered += 1;
          else missing.set(ch, (missing.get(ch) || 0) + 1);
        }
      }
    }
  }
  const rate = covered / total;
  const worst = [...missing.entries()].sort((a, b) => b[1] - a[1]).slice(0, 20);
  assert.ok(rate >= 0.97,
    `覆蓋率 ${(rate * 100).toFixed(1)}% 未達 97%，待補：${JSON.stringify(worst)}`);
});

test('詞典的鍵必須是純漢字（夾假名的鍵永遠匹配不到，留著會誤導）', () => {
  for (const base of buildLexicon(lexJson).keys()) {
    assert.ok(!/[\u3040-\u30ff]/.test(base),
      `${base} 夾有假名，annotateWithLexicon 只掃連續漢字段，這個鍵匹配不到`);
  }
});
