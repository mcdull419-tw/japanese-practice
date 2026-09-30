import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pickForPlayback } from '../../app/ui/player.js';

const items = [
  { id: 'a', covers: ['w:A'], answer: 'あ', prompt: { text: '甲' } },
  { id: 'b', covers: ['w:B'], answer: 'い', prompt: { text: '乙' } },
];
// A 全錯（不熟）、B 全對（熟）
const conceptStates = new Map([
  ['w:A', { A: 0, reps: 3 }],
  ['w:B', { A: 1, reps: 3 }],
]);

function countPicks(alpha) {
  let a = 0;
  for (let i = 0; i < 1000; i++) {
    const rng = () => (i + 0.5) / 1000;
    if (pickForPlayback(items, new Map(), conceptStates, 0, alpha, rng).id === 'a') a += 1;
  }
  return a;
}

test('不熟的字被抽中的機率明顯較高（規格 §6.3 加權隨機）', () => {
  const a = countPicks(1);
  assert.ok(a > 550, `不熟的字只被抽中 ${a}/1000 次，加權沒有作用`);
});

test('alpha 為 0 時退化為平均分布', () => {
  const a = countPicks(0);
  assert.ok(a > 400 && a < 600, `平均分布下應約各半，實得 ${a}/1000`);
});

test('alpha 越大越集中在生詞', () => {
  assert.ok(countPicks(2) >= countPicks(1), 'alpha 加大應更偏重生詞');
});

test('題庫為空時回傳 null 而非拋錯', () => {
  assert.equal(pickForPlayback([], new Map(), new Map(), 0, 1, () => 0.5), null);
});

test('完全沒練過（conceptStates 為空）時仍抽得出東西', () => {
  const it = pickForPlayback(items, new Map(), new Map(), 0, 1, () => 0.5);
  assert.ok(it && items.includes(it));
});

test('播放器不匯入 store，結構上就寫不了事件（規格 §6.3）', async () => {
  const { readFileSync } = await import('node:fs');
  const src = readFileSync(new URL('../../app/ui/player.js', import.meta.url), 'utf8');
  assert.ok(!/store|appendEvents|makeEvent/.test(src),
    '播放器不得寫入事件——純聆聽沒有作答，計入會虛報熟悉度');
});
