import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { conceptLabel, conceptsByPattern, requiresLessonOf } from '../../app/core/conceptdefs.js';
import { skillOf } from '../../app/core/concepts.js';

const defs = JSON.parse(readFileSync(new URL('../../data/concepts.json', import.meta.url)));

test('conceptLabel 查得到就回標籤，查不到回 id 本身', () => {
  const someId = Object.keys(defs)[0];
  assert.equal(conceptLabel(defs, someId), defs[someId].label);
  assert.equal(conceptLabel(defs, 'p:nonexistent:x'), 'p:nonexistent:x');
});

test('requiresLessonOf 查不到時回 1（不擋任何範圍）', () => {
  assert.equal(requiresLessonOf(defs, 'p:nonexistent:x'), 1);
});

test('conceptsByPattern 建出 pattern → 概念的反查表', () => {
  const map = conceptsByPattern(defs);
  assert.ok(map instanceof Map);
  for (const [pid, ids] of map) {
    assert.match(pid, /^L\d{2}-[AB]\d+$/, `pattern id 格式異常：${pid}`);
    assert.ok(ids.length > 0);
  }
});

// ── 以下為漂移偵測（規格 §13 決定 6）────────────────────────────

test('每個概念 id 都能被 skillOf 歸類（不得落入任何長條圖之外）', () => {
  for (const id of Object.keys(defs)) {
    assert.ok(skillOf(id) !== null, `概念 ${id} 無法歸入六類技能，檢查前綴`);
  }
});

test('每筆定義欄位齊備且無 skills 欄位', () => {
  for (const [id, d] of Object.entries(defs)) {
    assert.equal(typeof d.label, 'string', `${id} 缺 label`);
    assert.ok(d.label.length > 0, `${id} 的 label 為空`);
    assert.equal(typeof d.requires_lesson, 'number', `${id} 缺 requires_lesson`);
    assert.ok(d.requires_lesson >= 1 && d.requires_lesson <= 15, `${id} 的課次超出範圍`);
    assert.equal(typeof d.source_ref, 'string', `${id} 缺 source_ref`);
    assert.equal(d.skills, undefined, `${id} 不得自帶 skills 欄位（技能由 skillOf 推導）`);
  }
});

test('patterns 反查表的每個 pattern id 都真的存在於課本資料中', () => {
  const real = new Set();
  for (let n = 1; n <= 15; n++) {
    const d = JSON.parse(readFileSync(new URL(`../../data/lessons/${String(n).padStart(2, '0')}.json`, import.meta.url)));
    for (const p of d.patterns || []) real.add(p.id);
  }
  // 練習Ｂ（data/drills.json）也走同一張反查表——它與練習Ａ 的素材結構不同，
  // 但「這則練習考哪個概念」的對應關係是同一件事，不另立第二份對照表。
  const drills = JSON.parse(readFileSync(new URL('../../data/drills.json', import.meta.url)));
  for (const id of Object.keys(drills)) real.add(id);
  for (const [id, d] of Object.entries(defs)) {
    for (const pid of d.patterns || []) {
      assert.ok(real.has(pid), `概念 ${id} 引用了不存在的代入表 ${pid}`);
    }
  }
});

test('同一張代入表不得歸屬到兩個概念', () => {
  const owner = new Map();
  for (const [id, d] of Object.entries(defs)) {
    for (const pid of d.patterns || []) {
      assert.ok(!owner.has(pid), `代入表 ${pid} 同時屬於 ${owner.get(pid)} 與 ${id}`);
      owner.set(pid, id);
    }
  }
});

test('概念數量在合理範圍', () => {
  const n = Object.keys(defs).length;
  assert.ok(n >= 50 && n <= 130, `概念數 ${n} 不如預期（91則文法，預估 70~90 個概念）`);
});
