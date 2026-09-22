import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const marks = JSON.parse(readFileSync(new URL('../../data/particles.json', import.meta.url)));
const defs = JSON.parse(readFileSync(new URL('../../data/concepts.json', import.meta.url)));

function allSentences() {
  const out = new Map();
  for (let n = 1; n <= 15; n++) {
    const d = JSON.parse(readFileSync(new URL(`../../data/lessons/${String(n).padStart(2, '0')}.json`, import.meta.url)));
    for (const s of d.sentences || []) out.set(s.id, { ...s, lesson: n });
  }
  return out;
}

const sentences = allSentences();

test('每個標註的句子 id 都存在', () => {
  for (const sid of Object.keys(marks)) {
    assert.ok(sentences.has(sid), `particles.json 引用了不存在的句子 ${sid}`);
  }
});

// 這是本檔最重要的一項：課本語料若被重新抽取而位移，必須紅燈而非靜默錯位。
test('每個 at 位置在句子中確實是所標的助詞', () => {
  for (const [sid, list] of Object.entries(marks)) {
    const jp = sentences.get(sid).jp;
    for (const m of list) {
      const got = jp.slice(m.at, m.at + m.p.length);
      assert.equal(got, m.p,
        `${sid} 的 at=${m.at} 應為「${m.p}」，實際是「${got}」——課本語料可能已位移`);
    }
  }
});

test('每個概念引用都存在於 concepts.json，不得懸空', () => {
  for (const [sid, list] of Object.entries(marks)) {
    for (const m of list) {
      assert.ok(m.c && m.c.length > 0, `${sid} 的 at=${m.at} 尚未填入概念 id`);
      assert.ok(Object.hasOwn(defs, m.c), `${sid} 引用了 concepts.json 沒有的概念 ${m.c}`);
    }
  }
});

test('同一句中的標註位置不重複且遞增', () => {
  for (const [sid, list] of Object.entries(marks)) {
    const ats = list.map((m) => m.at);
    assert.deepEqual([...ats].sort((a, b) => a - b), ats, `${sid} 的標註未依位置排序`);
    assert.equal(new Set(ats).size, ats.length, `${sid} 有重複的標註位置`);
  }
});

test('只標註 文型 與 例文 段落', () => {
  for (const sid of Object.keys(marks)) {
    const sec = sentences.get(sid).section;
    assert.ok(['文型', '例文'].includes(sec), `${sid} 屬於 ${sec} 段落，不應納入`);
  }
});

test('標註總數在預期範圍', () => {
  const n = Object.values(marks).reduce((a, l) => a + l.length, 0);
  assert.ok(n >= 200 && n <= 350, `標註數 ${n} 不如預期（文型＋例文 約 296 個句末助詞）`);
});
