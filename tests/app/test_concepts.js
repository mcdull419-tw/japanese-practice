import { test } from 'node:test';
import assert from 'node:assert/strict';
import { SKILLS, skillOf, conceptsForVocab, conceptsForConjugation, aggregateSkills }
  from '../../app/core/concepts.js';

test('技能歸屬：後綴優先於前綴', () => {
  assert.equal(skillOf('w:きります'), '單字');
  assert.equal(skillOf('w:てがみ:reading'), '讀音');
  assert.equal(skillOf('w:きります:group'), '變化');
  assert.equal(skillOf('r:te:groupI'), '變化');
  assert.equal(skillOf('p:に:recipient'), '助詞');
  assert.equal(skillOf('g:mou_mashita'), '句型');
  assert.equal(skillOf('c:hon'), '數量');
  assert.equal(skillOf('n:time:hour'), '數量');
  assert.equal(skillOf('zzz:unknown'), null);
});

test('有漢字的單字產生字義與讀音兩個概念（以引用形為 lemma）', () => {
  const ids = conceptsForVocab({ kana: 'きります', kanji: '切ります', zh: '剪，切' });
  assert.deepEqual(ids.sort(), ['w:切ります', 'w:切ります:reading'].sort());
});

test('無漢字的單字只產生字義概念（引用形退回假名）', () => {
  const ids = conceptsForVocab({ kana: 'あげます', kanji: null, zh: '給，送' });
  assert.deepEqual(ids, ['w:あげます']);
});

test('概念用引用形：同假名不同詞分開，同詞跨課共用', () => {
  const oki = conceptsForVocab({ kana: 'おきます', kanji: '起きます' });
  const oku = conceptsForVocab({ kana: 'おきます', kanji: '置きます' });
  assert.notDeepEqual(oki, oku, '起きる 與 置く 是不同概念');

  const y4 = conceptsForVocab({ kana: 'やすみます', kanji: '休みます' });
  const y11 = conceptsForVocab({ kana: 'やすみます', kanji: '休みます' });
  assert.deepEqual(y4, y11, '同一個詞跨課次應共用概念');
});

test('變化題涵蓋規則與該動詞的分類', () => {
  const ids = conceptsForConjugation('かきます', 'I', 'te');
  assert.ok(ids.includes('r:te:groupI'));
  assert.ok(ids.includes('w:かきます:group'));
});

test('技能熟悉度為算術平均，不加 log(1+reps) 權重', () => {
  const conceptStates = new Map([
    ['w:a', { A: 1.0, reps: 1 }],
    ['w:b', { A: 0.0, reps: 100 }],
  ]);
  const { scores } = aggregateSkills(conceptStates, ['w:a', 'w:b']);
  assert.equal(scores['單字'], 0.5, '純算術平均，不因 reps 不同而偏向任一邊');
});

test('回歸測試（核心 bug）：範圍內 10 個概念、只練過 2 個且都全對 → 0.2，不是 1.0', () => {
  const conceptStates = new Map([
    ['w:a', { A: 1.0, reps: 5 }],
    ['w:b', { A: 1.0, reps: 3 }],
  ]);
  const scope = ['w:a', 'w:b', 'w:c', 'w:d', 'w:e', 'w:f', 'w:g', 'w:h', 'w:i', 'w:j'];
  const { scores, counts } = aggregateSkills(conceptStates, scope);
  assert.equal(scores['單字'], 0.2);
  assert.deepEqual(counts['單字'], { practiced: 2, total: 10 });
});

test('未考過的概念以 A=0 計入分母，不是排除在外', () => {
  const conceptStates = new Map(); // 完全沒練過
  const { scores, counts } = aggregateSkills(conceptStates, ['w:a', 'w:b']);
  assert.equal(scores['單字'], 0);
  assert.deepEqual(counts['單字'], { practiced: 0, total: 2 });
});

test('範圍內完全沒有該技能的概念時，score 為 null（不同於「有概念但都是 0 分」）', () => {
  const { scores } = aggregateSkills(new Map([['w:a', { A: 0.8, reps: 3 }]]), ['w:a']);
  assert.ok(scores['單字'] > 0);
  assert.equal(scores['助詞'], null);
});
