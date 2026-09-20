import { test } from 'node:test';
import assert from 'node:assert/strict';
import { retrievability, initialState, updateState, replay, SRS_CONST } from '../../app/core/srs.js';

const near = (a, b, tol = 0.01) => assert.ok(Math.abs(a - b) < tol, `${a} vs ${b}`);

test('衰減曲線符合規格 §7.2 的表', () => {
  near(retrievability(3, 3), 0.90);     // S=3 天，3 天後 90%
  near(retrievability(3, 7), 0.79);
  near(retrievability(3, 30), 0.47);
  near(retrievability(30, 30), 0.90);   // S=30 天，30 天後才 90%
  near(retrievability(30, 90), 0.75);
  near(retrievability(3, 0), 1.00);     // 剛複習完
});

test('練得越熟，同樣天數衰減越慢', () => {
  assert.ok(retrievability(30, 7) > retrievability(3, 7));
});

test('首次作答依 grade 給初始狀態', () => {
  assert.equal(initialState(1).S, 0.4);
  assert.equal(initialState(4).S, 9.0);
  assert.ok(initialState(1).D > initialState(4).D);  // 答錯者難度較高
});

test('答對時 S 增加；在快遺忘時答對增益最大（規格 §7.3）', () => {
  const s = { S: 3, D: 5 };
  // R=1 時 (e^(1-R) - 1) 精確為 0，增益必為 0——同日重複複習不給穩定度增益。
  // 這是長期記憶模型的正確行為：兩分鐘後再答對一次，不代表記得更久。
  assert.equal(updateState(s, 3, 0).S, 3, 'elapsed=0 時 S 不變（增益精確為 0）');

  const lateWin = updateState(s, 3, 20).S;   // R≈0.31，快忘掉才答對
  const earlyWin = updateState(s, 3, 1).S;   // R≈0.96
  assert.ok(lateWin > earlyWin, `晚答對應增益更大: ${lateWin} vs ${earlyWin}`);
  assert.ok(earlyWin > 3, '有經過時間就該有增益');
});

test('S 越大增幅越小（邊際遞減）', () => {
  const gain = (S) => updateState({ S, D: 5 }, 3, S).S / S;
  assert.ok(gain(3) > gain(30), '高 S 的相對增幅應較小');
});

test('難題（D 高）的 S 增幅較小', () => {
  const easy = updateState({ S: 3, D: 2 }, 3, 3).S;
  const hard = updateState({ S: 3, D: 9 }, 3, 3).S;
  assert.ok(easy > hard);
});

test('答錯時 S 縮水但不歸零，D 上調', () => {
  const next = updateState({ S: 10, D: 5 }, 1, 5);
  assert.ok(next.S < 10 && next.S >= SRS_CONST.S_MIN, `S=${next.S}`);
  assert.ok(next.D > 5);
});

test('D 夾在 1..10', () => {
  let st = { S: 3, D: 9.8 };
  for (let i = 0; i < 10; i++) st = updateState(st, 1, 1);
  assert.ok(st.D <= 10);
  st = { S: 3, D: 1.2 };
  for (let i = 0; i < 10; i++) st = updateState(st, 4, 1);
  assert.ok(st.D >= 1);
});

test('replay 從事件日誌重建狀態，且與事件順序無關（會先排序）', () => {
  const day = 86400;
  const now = 1000 * day;
  const evs = [
    { i: 'a', t: now - 10 * day, g: 3 },
    { i: 'a', t: now - 3 * day, g: 3 },
    { i: 'b', t: now - 1 * day, g: 1 },
  ];
  const m1 = replay(evs, now);
  const m2 = replay([...evs].reverse(), now);
  assert.equal(m1.get('a').reps, 2);
  assert.equal(m1.get('b').lapses, 1);
  assert.deepEqual(m1.get('a'), m2.get('a'), 'replay 必須先排序，與輸入順序無關');
  assert.ok(m1.get('a').R > 0 && m1.get('a').R <= 1);
});
