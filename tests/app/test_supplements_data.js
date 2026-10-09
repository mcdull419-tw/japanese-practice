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
