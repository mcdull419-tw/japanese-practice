import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readCounter, COUNTERS } from '../../app/lang/counters.js';

test('ほん：1 3 6 8 10 音變', () => {
  assert.equal(readCounter(1, 'hon'), 'いっぽん');
  assert.equal(readCounter(2, 'hon'), 'にほん');
  assert.equal(readCounter(3, 'hon'), 'さんぼん');
  assert.equal(readCounter(4, 'hon'), 'よんほん');
  assert.equal(readCounter(6, 'hon'), 'ろっぽん');
  assert.equal(readCounter(8, 'hon'), 'はっぽん');
  assert.equal(readCounter(10, 'hon'), 'じゅっぽん');
});

test('さつ：1 8 10 促音', () => {
  assert.equal(readCounter(1, 'satsu'), 'いっさつ');
  assert.equal(readCounter(3, 'satsu'), 'さんさつ');
  assert.equal(readCounter(8, 'satsu'), 'はっさつ');
  assert.equal(readCounter(10, 'satsu'), 'じゅっさつ');
});

test('ひき：1 3 6 8 10 音變', () => {
  assert.equal(readCounter(1, 'hiki'), 'いっぴき');
  assert.equal(readCounter(3, 'hiki'), 'さんびき');
  assert.equal(readCounter(6, 'hiki'), 'ろっぴき');
  assert.equal(readCounter(8, 'hiki'), 'はっぴき');
});

test('にん：1 2 4 為不規則', () => {
  assert.equal(readCounter(1, 'nin'), 'ひとり');
  assert.equal(readCounter(2, 'nin'), 'ふたり');
  assert.equal(readCounter(3, 'nin'), 'さんにん');
  assert.equal(readCounter(4, 'nin'), 'よにん');
  assert.notEqual(readCounter(4, 'nin'), 'よんにん');
});

test('さい：1 8 10 促音、20 為はたち', () => {
  assert.equal(readCounter(1, 'sai'), 'いっさい');
  assert.equal(readCounter(8, 'sai'), 'はっさい');
  assert.equal(readCounter(10, 'sai'), 'じゅっさい');
});

test('まい、だい 無音變', () => {
  assert.equal(readCounter(1, 'mai'), 'いちまい');
  assert.equal(readCounter(3, 'mai'), 'さんまい');
  assert.equal(readCounter(1, 'dai'), 'いちだい');
  assert.equal(readCounter(8, 'dai'), 'はちだい');
});

test('かい（樓層）：1 3 6 8 10 音變', () => {
  assert.equal(readCounter(1, 'kai_floor'), 'いっかい');
  assert.equal(readCounter(3, 'kai_floor'), 'さんがい');
  assert.equal(readCounter(6, 'kai_floor'), 'ろっかい');
  assert.equal(readCounter(10, 'kai_floor'), 'じゅっかい');
});

test('かい（次數）：6 為ろっかい，與樓層不同在 3 不濁化', () => {
  assert.equal(readCounter(1, 'kai_times'), 'いっかい');
  assert.equal(readCounter(3, 'kai_times'), 'さんかい');
  assert.equal(readCounter(6, 'kai_times'), 'ろっかい');
  assert.equal(readCounter(10, 'kai_times'), 'じゅっかい');
});

test('えん、ねん、じかん：4 為よ、じかん 的 7 9 同時刻', () => {
  assert.equal(readCounter(4, 'en'), 'よえん');
  assert.equal(readCounter(3, 'en'), 'さんえん');
  assert.equal(readCounter(4, 'nen'), 'よねん');
  assert.equal(readCounter(4, 'jikan'), 'よじかん');
  assert.equal(readCounter(7, 'jikan'), 'しちじかん');
  assert.equal(readCounter(9, 'jikan'), 'くじかん');
});

test('COUNTERS 每筆欄位齊備，課次在 1~15', () => {
  for (const [key, c] of Object.entries(COUNTERS)) {
    assert.equal(typeof c.kana, 'string', `${key} 缺 kana`);
    assert.equal(typeof c.label, 'string', `${key} 缺 label`);
    assert.ok(c.lesson >= 1 && c.lesson <= 15, `${key} 的 lesson 超出範圍：${c.lesson}`);
  }
});

test('每個量詞 1~10 都算得出來，不拋錯', () => {
  for (const key of Object.keys(COUNTERS)) {
    for (let n = 1; n <= 10; n++) {
      assert.doesNotThrow(() => readCounter(n, key), `${key} 的 ${n} 失敗`);
      assert.ok(readCounter(n, key).length > 0);
    }
  }
});

test('未知量詞與超出範圍時拋錯', () => {
  assert.throws(() => readCounter(1, 'nope'));
  assert.throws(() => readCounter(0, 'hon'));
  assert.throws(() => readCounter(11, 'hon'));
});
