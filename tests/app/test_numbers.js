import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readNumber, readHour, readMinute, readDayOfMonth, readMonth } from '../../app/lang/numbers.js';

test('基本數字 1~10', () => {
  const want = ['いち', 'に', 'さん', 'よん', 'ご', 'ろく', 'なな', 'はち', 'きゅう', 'じゅう'];
  want.forEach((w, i) => assert.equal(readNumber(i + 1), w));
});

test('十位與百位', () => {
  assert.equal(readNumber(11), 'じゅういち');
  assert.equal(readNumber(20), 'にじゅう');
  assert.equal(readNumber(35), 'さんじゅうご');
  assert.equal(readNumber(99), 'きゅうじゅうきゅう');
  assert.equal(readNumber(100), 'ひゃく');
  assert.equal(readNumber(300), 'さんびゃく');
  assert.equal(readNumber(600), 'ろっぴゃく');
  assert.equal(readNumber(800), 'はっぴゃく');
  assert.equal(readNumber(1000), 'せん');
  assert.equal(readNumber(3000), 'さんぜん');
  assert.equal(readNumber(8000), 'はっせん');
});

test('時刻：4時 7時 9時 為不規則', () => {
  assert.equal(readHour(4), 'よじ');
  assert.notEqual(readHour(4), 'しじ');
  assert.equal(readHour(7), 'しちじ');
  assert.equal(readHour(9), 'くじ');
  assert.equal(readHour(1), 'いちじ');
  assert.equal(readHour(12), 'じゅうにじ');
});

test('分：1 3 4 6 8 10 有音變', () => {
  assert.equal(readMinute(1), 'いっぷん');
  assert.equal(readMinute(2), 'にふん');
  assert.equal(readMinute(3), 'さんぷん');
  assert.equal(readMinute(4), 'よんぷん');
  assert.equal(readMinute(5), 'ごふん');
  assert.equal(readMinute(6), 'ろっぷん');
  assert.equal(readMinute(8), 'はっぷん');
  assert.equal(readMinute(10), 'じゅっぷん');
  assert.equal(readMinute(30), 'さんじゅっぷん');
  assert.equal(readMinute(15), 'じゅうごふん');
});

test('日期：1~10、14、20、24 為不規則', () => {
  assert.equal(readDayOfMonth(1), 'ついたち');
  assert.equal(readDayOfMonth(2), 'ふつか');
  assert.equal(readDayOfMonth(3), 'みっか');
  assert.equal(readDayOfMonth(4), 'よっか');
  assert.equal(readDayOfMonth(5), 'いつか');
  assert.equal(readDayOfMonth(6), 'むいか');
  assert.equal(readDayOfMonth(7), 'なのか');
  assert.equal(readDayOfMonth(8), 'ようか');
  assert.equal(readDayOfMonth(9), 'ここのか');
  assert.equal(readDayOfMonth(10), 'とおか');
  assert.equal(readDayOfMonth(14), 'じゅうよっか');
  assert.equal(readDayOfMonth(20), 'はつか');
  assert.notEqual(readDayOfMonth(20), 'にじゅうにち');
  assert.equal(readDayOfMonth(24), 'にじゅうよっか');
});

test('日期：規則部分', () => {
  assert.equal(readDayOfMonth(11), 'じゅういちにち');
  assert.equal(readDayOfMonth(31), 'さんじゅういちにち');
});

test('月份：4月 7月 9月 為不規則', () => {
  assert.equal(readMonth(4), 'しがつ');
  assert.notEqual(readMonth(4), 'よんがつ');
  assert.equal(readMonth(7), 'しちがつ');
  assert.equal(readMonth(9), 'くがつ');
  assert.equal(readMonth(1), 'いちがつ');
  assert.equal(readMonth(12), 'じゅうにがつ');
});

test('超出範圍時拋錯', () => {
  assert.throws(() => readHour(13));
  assert.throws(() => readHour(0));
  assert.throws(() => readMinute(60));
  assert.throws(() => readDayOfMonth(32));
  assert.throws(() => readMonth(13));
  assert.throws(() => readNumber(0));
});
