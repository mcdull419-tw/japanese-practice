import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import {
  readNumber, readBig, readDecimal, readFraction, readZero, NUMBER_ALTS,
} from '../../app/lang/numbers.js';

// 補充講義的轉寫檔只當對照基準：執行期不讀，這裡逐筆比對程式的讀音表。
const load = (name) => JSON.parse(readFileSync(new URL(`../../data/supplements/${name}.json`, import.meta.url), 'utf8'));

function checkShape(file) {
  assert.ok(file.source.endsWith('.jpeg'));
  const keys = new Set();
  for (const r of file.rows) {
    assert.ok(r.key && r.label, `缺 key/label: ${JSON.stringify(r)}`);
    assert.ok(!keys.has(r.key), `key 重複: ${r.key}`);
    keys.add(r.key);
    assert.ok(Array.isArray(r.read) && r.read.length > 0, `${r.key} 缺 read`);
    for (const k of r.read) assert.match(k, /^[ぁ-ゟー]+$|^ゼロ$/, `${r.key} 的讀音含非假名: ${k}`);
  }
}

test('numbers.json 格式正確', () => checkShape(load('numbers')));

test('numbers.json 與 numbers.js 一致', () => {
  for (const r of load('numbers').rows) {
    const n = Number(r.key);
    let got;
    if (r.key.includes('/')) { const [a, b] = r.key.split('/').map(Number); got = readFraction(a, b); }
    else if (r.key.includes('.')) got = readDecimal(r.key);
    else if (n === 0) got = readZero()[0];
    else if (n >= 10000) got = readBig(n);
    else got = readNumber(n);
    assert.equal(got, r.read[0], `${r.key}: 講義 ${r.read[0]}，程式 ${got}`);
  }
});

test('並列讀法都被接受（NUMBER_ALTS 涵蓋講義的其餘讀法）', () => {
  for (const r of load('numbers').rows) {
    const alts = NUMBER_ALTS[r.key] || [];
    assert.deepEqual(alts, r.read.slice(1), `${r.key} 的並列讀法與 NUMBER_ALTS 不符`);
  }
});

import { TIMEWORDS } from '../../app/lang/timewords.js';

test('timewords.json 格式正確', () => checkShape(load('timewords')));

test('timewords.json 與 timewords.js 逐筆一致', () => {
  const byKey = new Map(TIMEWORDS.map((t) => [t.key, t]));
  const rows = load('timewords').rows;
  for (const r of rows) {
    const t = byKey.get(r.key);
    assert.ok(t, `timewords.js 缺 ${r.key}（${r.label}）`);
    assert.equal(t.label, r.label, `${r.key}: 書寫不符`);
    assert.equal(t.zh, r.note, `${r.key}: 中文不符`);
    assert.equal(t.kana, r.read[0], `${r.key}: 第一讀法不符`);
    assert.deepEqual(t.alts, r.read.slice(1), `${r.key}: 並列讀法不符`);
  }
  assert.equal(TIMEWORDS.length, rows.length, 'timewords.js 多出講義沒有的條目');
});

import { readHour, readMinute, readDayOfMonth, readMonth, CLOCK_ALTS, CLOCK_Q } from '../../app/lang/numbers.js';

test('clock-date.json 格式正確', () => checkShape(load('clock-date')));

test('clock-date.json 與 numbers.js 一致', () => {
  const fn = { hour: readHour, minute: readMinute, month: readMonth, day: readDayOfMonth };
  for (const r of load('clock-date').rows) {
    const [kind, v] = r.key.split(':');
    if (v === 'q') { assert.equal(CLOCK_Q[kind], r.read[0], `${r.key}: 疑問詞不符`); continue; }
    if (v === 'half') { assert.equal(CLOCK_Q.half, r.read[0], '半 不符'); continue; }
    const got = fn[kind](Number(v));
    assert.equal(got, r.read[0], `${r.key}: 講義 ${r.read[0]}，程式 ${got}`);
    assert.deepEqual(CLOCK_ALTS[r.key] || [], r.read.slice(1), `${r.key}: 並列讀法與 CLOCK_ALTS 不符`);
  }
});

test('17日、27日 唸 しち，19日、29日 唸 く（不是なな、きゅう）', () => {
  assert.equal(readDayOfMonth(17), 'じゅうしちにち');
  assert.equal(readDayOfMonth(27), 'にじゅうしちにち');
  assert.equal(readDayOfMonth(19), 'じゅうくにち');
  assert.equal(readDayOfMonth(29), 'にじゅうくにち');
});

import { readCounter, readCounterAlts, readCounterQ } from '../../app/lang/counters.js';

test('periods.json 格式正確', () => checkShape(load('periods')));

test('periods.json 與 counters.js／numbers.js 一致', () => {
  const map = { jikan: 'jikan', nen: 'nen', shuukan: 'shuukan', kagetsu: 'kagetsu', nichi: 'nichi_span' };
  for (const r of load('periods').rows) {
    const [kind, v] = r.key.split(':');
    if (kind === 'fun') {                             // 分鐘與時刻的分同表
      if (v === 'q') assert.equal(CLOCK_Q.minute, r.read[0]);
      else {
        assert.equal(readMinute(Number(v)), r.read[0], `${r.key}`);
        assert.deepEqual(CLOCK_ALTS[`minute:${v}`] || [], r.read.slice(1), `${r.key}: 並列讀法`);
      }
      continue;
    }
    const key = map[kind];
    if (v === 'q') { assert.equal(readCounterQ(key), r.read[0], `${r.key}: 疑問詞`); continue; }
    assert.equal(readCounter(Number(v), key), r.read[0], `${r.key}: 講義 ${r.read[0]}`);
    assert.deepEqual(readCounterAlts(Number(v), key), r.read.slice(1), `${r.key}: 並列讀法與 alts 不符`);
  }
});

test('4時間是よじかん、不是よんじかん', () => {
  assert.equal(readCounter(4, 'jikan'), 'よじかん');
});

test('1天（期間）是いちにち，與日期的ついたち不同', () => {
  assert.equal(readCounter(1, 'nichi_span'), 'いちにち');
  assert.equal(readCounter(2, 'nichi_span'), 'ふつか');
});

import { COUNTERS } from '../../app/lang/counters.js';

test('counters.json 格式正確', () => checkShape(load('counters')));

test('counters.json 與 counters.js 逐筆一致，且 alts 與講義並列讀法相同', () => {
  for (const r of load('counters').rows) {
    const [key, v] = r.key.split(':');
    if (v === 'q') { assert.equal(readCounterQ(key), r.read[0], `${r.key}: 疑問詞`); continue; }
    assert.equal(readCounter(Number(v), key), r.read[0], `${r.key}: 講義 ${r.read[0]}`);
    assert.deepEqual(readCounterAlts(Number(v), key), r.read.slice(1), `${r.key}: 並列讀法與 alts 不符`);
  }
});

test('講義上每種量詞在程式裡都有，且程式沒有多收講義沒有的量詞（en 除外）', () => {
  const inJson = new Set(load('counters').rows.map((r) => r.key.split(':')[0]));
  for (const k of inJson) assert.ok(COUNTERS[k], `COUNTERS 缺 ${k}`);
  const periods = new Set(load('periods').rows.map((r) => r.key.split(':')[0]));
  const known = new Set(['en', 'jikan', 'nen', 'nichi_span', 'shuukan', 'kagetsu']);
  for (const k of Object.keys(COUNTERS)) {
    assert.ok(inJson.has(k) || known.has(k) || periods.has(k), `COUNTERS 多出講義沒有的 ${k}`);
  }
});

test('疑問詞連濁：なんぼん／なんびき／なんがい／なんぞく／なんげん／なんばい', () => {
  assert.equal(readCounterQ('hon'), 'なんぼん');
  assert.equal(readCounterQ('hiki'), 'なんびき');
  assert.equal(readCounterQ('kai_floor'), 'なんがい');
  assert.equal(readCounterQ('soku'), 'なんぞく');
  assert.equal(readCounterQ('ken'), 'なんげん');
  assert.equal(readCounterQ('hai'), 'なんばい');
});
