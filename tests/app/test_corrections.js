import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { exportFlagged, applyCorrections } from '../../app/core/corrections.js';
import { generate as genDrills } from '../../app/generators/drills.js';

const item = (over = {}) => ({
  id: 'drill:L08-B2:0', engine: 'substitute',
  prompt: { type: 'text', text: '例：…\n用這個提示造句：ミラーさん・忙しい' },
  answer: 'ミラーさんは 忙しくないです。', alternatives: [],
  source_ref: '第8課 練習Ｂ-2', covers: ['g:adj_predicate'], ...over,
});

test('exportFlagged 帶出題幹與正解，才有辦法離站查證', () => {
  const items = new Map([[item().id, item()]]);
  const out = exportFlagged(new Map([[item().id, 1700000000]]), items);
  assert.equal(out.length, 1);
  assert.equal(out[0].id, 'drill:L08-B2:0');
  assert.equal(out[0].answer, 'ミラーさんは 忙しくないです。');
  assert.equal(out[0].source_ref, '第8課 練習Ｂ-2');
  assert.match(out[0].flagged_at, /^\d{4}-\d{2}-\d{2}T/);
});

test('題目不在本輪題庫時仍匯出 id，不整個漏掉', () => {
  const out = exportFlagged(new Map([['drill:L99-B9:0', 1700000000]]), new Map());
  assert.equal(out.length, 1);
  assert.equal(out[0].id, 'drill:L99-B9:0');
  assert.equal(out[0].answer, null);
});

test('applyCorrections 覆蓋答案與題幹，未列出的欄位不動', () => {
  const [fixed] = applyCorrections([item()], {
    'drill:L08-B2:0': { answer: 'ミラーさんは 忙しく ないです。' },
  });
  assert.equal(fixed.answer, 'ミラーさんは 忙しく ないです。');
  assert.equal(fixed.source_ref, '第8課 練習Ｂ-2', '沒被更正的欄位不該變動');
  assert.deepEqual(fixed.covers, ['g:adj_predicate']);
});

test('alternatives 是疊加而非取代（不得抹掉生成器算出的合法寫法）', () => {
  const base = item({ alternatives: ['ミラーさんは いそがしくないです。'] });
  const [fixed] = applyCorrections([base], {
    'drill:L08-B2:0': { alternatives: ['ミラーさんは 忙しく ありません。'] },
  });
  assert.equal(fixed.alternatives.length, 2);
  assert.ok(fixed.alternatives.includes('ミラーさんは いそがしくないです。'));
  assert.ok(fixed.alternatives.includes('ミラーさんは 忙しく ありません。'));
});

test('沒有更正檔時原樣回傳，不做多餘的複製', () => {
  const items = [item()];
  assert.equal(applyCorrections(items, {}), items);
  assert.equal(applyCorrections(items, null), items);
});

// ── 漂移偵測（規格 §13 決定 6）────────────────────────────────

test('corrections.json 的每筆更正都對得上實際存在的題目', () => {
  let corrections;
  try {
    corrections = JSON.parse(readFileSync(
      new URL('../../data/corrections.json', import.meta.url)));
  } catch {
    return; // 還沒有任何更正時，這個檔可以不存在
  }
  const drills = JSON.parse(readFileSync(new URL('../../data/drills.json', import.meta.url)));
  const known = new Set([...genDrills(drills, new Map())].map((x) => x.id));
  for (const id of Object.keys(corrections)) {
    // 目前只有練習Ｂ 需要這條路；其他題型的 id 先放行，日後擴充時再收緊。
    if (!id.startsWith('drill:')) continue;
    assert.ok(known.has(id),
      `更正 ${id} 指向不存在的題目——題庫改過之後這筆更正已成孤兒，請清掉`);
  }
});
