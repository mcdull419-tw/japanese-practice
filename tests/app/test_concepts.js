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

test('有漢字的單字產生字義與讀音兩個概念', () => {
  const ids = conceptsForVocab({ kana: 'きります', kanji: '切ります', zh: '剪，切' });
  assert.deepEqual(ids.sort(), ['w:きります', 'w:きります:reading'].sort());
});

test('無漢字的單字只產生字義概念', () => {
  const ids = conceptsForVocab({ kana: 'あげます', kanji: null, zh: '給，送' });
  assert.deepEqual(ids, ['w:あげます']);
});

test('變化題涵蓋規則與該動詞的分類', () => {
  const ids = conceptsForConjugation('かきます', 'I', 'te');
  assert.ok(ids.includes('r:te:groupI'));
  assert.ok(ids.includes('w:かきます:group'));
});

test('技能聚合以 log(1+reps) 加權', () => {
  const m = new Map([
    ['w:a', { R: 1.0, reps: 1 }],    // 只練過一次
    ['w:b', { R: 0.0, reps: 100 }],  // 練過很多次但很生疏
  ]);
  const agg = aggregateSkills(m);
  assert.ok(agg['單字'] < 0.3, `練得多的生疏概念應主導: ${agg['單字']}`);
});

test('無資料的技能回傳 null 而非 0（尚未練過 ≠ 熟悉度 0）', () => {
  const agg = aggregateSkills(new Map([['w:a', { R: 0.8, reps: 3 }]]));
  assert.ok(agg['單字'] > 0);
  assert.equal(agg['助詞'], null);
});
