import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate, ENGINE } from '../../app/generators/recall.js';
import { isCorrect } from '../../app/core/normalize.js';

const V = [
  { kana: 'きります', kanji: '切ります', zh: '剪，切', lesson: 7, category: 'numbered', group: null },
  { kana: 'あげます', kanji: null, zh: '給，送', lesson: 7, category: 'numbered', group: null },
];

test('有漢字者產生兩題，無漢字者只產生一題', () => {
  const items = [...generate(V)];
  const ids = items.map((i) => i.id);
  assert.ok(ids.includes('recall:きります:zh2jp'));
  assert.ok(ids.includes('recall:きります:kanji2kana'));
  assert.ok(ids.includes('recall:あげます:zh2jp'));
  assert.equal(ids.includes('recall:あげます:kanji2kana'), false);
  assert.equal(items.length, 3);
});

test('zh2jp：題幹為中文，答案為假名，漢字列入 alternatives', () => {
  const it = [...generate(V)].find((i) => i.id === 'recall:きります:zh2jp');
  assert.equal(it.prompt.text, '剪，切');
  assert.equal(it.answer, 'きります');
  assert.ok(it.alternatives.includes('切ります'));
  assert.equal(it.engine, ENGINE);
});

test('kanji2kana：考讀音，covers 含 reading 概念（概念以引用形為 lemma）', () => {
  const it = [...generate(V)].find((i) => i.id === 'recall:きります:kanji2kana');
  assert.equal(it.prompt.text, '切ります');
  assert.equal(it.answer, 'きります');
  // 概念層以引用形（漢字優先）為 lemma，故 covers 是 w:切ります:reading，
  // 不是 w:きります:reading——item id 與 concept id 是不同命名空間。
  assert.ok(it.covers.includes('w:切ります:reading'));
  assert.ok(it.skills.includes('讀音'));
  assert.deepEqual(it.alternatives, [], '考讀音時不接受漢字作答');
});

test('requires_lesson 等於單字所在課次，source_ref 可讀', () => {
  const it = [...generate(V)][0];
  assert.equal(it.requires_lesson, 7);
  assert.ok(it.source_ref.includes('第7課'));
});

test('漢字欄用分隔符列出多個寫法時，各寫法各自成為 alternative，原始整串也保留（修正 B）', () => {
  const multi = [{ kana: 'つくります', kanji: '作ります、造ります', zh: '做，製造', lesson: 15, no: 5 }];
  const it = [...generate(multi)].find((i) => i.id === 'recall:つくります:zh2jp');
  assert.ok(it.alternatives.includes('作ります'));
  assert.ok(it.alternatives.includes('造ります'));
  assert.ok(it.alternatives.includes('作ります、造ります'), '原始整串也保留');
  assert.ok(isCorrect('作ります', it.answer, it.alternatives), '只打其中一個寫法應算對');
  assert.ok(isCorrect('造ります', it.answer, it.alternatives), '打另一個寫法也應算對');
});

test('kanji2kana 題不受漢字分隔符拆分影響，alternatives 維持空陣列（考讀音時不接受漢字）', () => {
  const multi = [{ kana: 'あつい', kanji: '暑い、熱い', zh: '熱', lesson: 8, no: 1 }];
  const it = [...generate(multi)].find((i) => i.id === 'recall:あつい:kanji2kana');
  assert.equal(it.prompt.text, '暑い、熱い');
  assert.deepEqual(it.alternatives, []);
});

test('假名欄用分隔符列出多個說法時，各說法各自成為 alternative，只打其中一種也算對', () => {
  const multi = [{ kana: 'おっと／しゅじん', kanji: '夫／主人', zh: '丈夫', lesson: 9, no: 1 }];
  const it = [...generate(multi)].find((i) => i.id === 'recall:おっと／しゅじん:zh2jp');
  assert.ok(it.alternatives.includes('おっと'));
  assert.ok(it.alternatives.includes('しゅじん'));
  assert.ok(isCorrect('おっと', it.answer, it.alternatives), '只打其中一種假名說法應算對');
  assert.ok(isCorrect('しゅじん', it.answer, it.alternatives), '打另一種假名說法也應算對');
});

test('假名欄用分隔符列出三個以上說法時同樣全部算對（公司名例）', () => {
  const multi = [{ kana: 'IMC／パワーでんき／ブラジルエアー', kanji: 'IMC／パワー電気／ブラジルエアー', zh: '公司名', lesson: 1, no: null }];
  const it = [...generate(multi)].find((i) => i.id === 'recall:IMC／パワーでんき／ブラジルエアー:zh2jp');
  assert.ok(isCorrect('IMC', it.answer, it.alternatives));
  assert.ok(isCorrect('パワーでんき', it.answer, it.alternatives));
  assert.ok(isCorrect('ブラジルエアー', it.answer, it.alternatives));
});

test('假名欄含句子標點「、」時不得被拆開（那是標點，不是多種說法）', () => {
  const sentence = [{ kana: 'いいえ、けっこうです。', kanji: null, zh: '不用了，夠了。', lesson: 8, no: null }];
  const it = [...generate(sentence)].find((i) => i.id === 'recall:いいえ、けっこうです。:zh2jp');
  assert.deepEqual(it.alternatives, ['いいえ、けっこうです。'], '不含「、」切開後的片段');
  assert.equal(isCorrect('いいえ', it.answer, it.alternatives), false, '句子標點拆出的片段不該算對');
  assert.ok(isCorrect('いいえ、けっこうです。', it.answer, it.alternatives), '完整句子仍算對');
});

test('重新生成得到相同 id（決定性）', () => {
  const a = [...generate(V)].map((i) => i.id);
  const b = [...generate(V)].map((i) => i.id);
  assert.deepEqual(a, b);
});

// ── 日→中選擇題（需求 #1 的另一個方向，Phase 1 延後至 2b）────────────
const jpVocab = [
  { kana: 'きります', kanji: '切ります', zh: '剪，切', lesson: 7, no: 1 },
  { kana: 'おくります', kanji: '送ります', zh: '寄送', lesson: 7, no: 2 },
  { kana: 'あげます', kanji: null, zh: '給，送', lesson: 7, no: 3 },
  { kana: 'もらいます', kanji: null, zh: '接受，得到', lesson: 7, no: 4 },
  { kana: 'かします', kanji: '貸します', zh: '借出', lesson: 7, no: 5 },
];

test('jp2zh 產出四選一，含正解', () => {
  const it = [...generate(jpVocab)].find((x) => x.id === 'recall:きります:jp2zh');
  assert.ok(it, '應產生 recall:きります:jp2zh');
  assert.equal(it.engine, 'recall');
  assert.equal(it.prompt.text, '切ります');
  assert.equal(it.answer, '剪，切');
  assert.equal(it.choices.length, 4);
  assert.ok(it.choices.includes('剪，切'));
  assert.equal(new Set(it.choices).size, 4, '選項不得重複');
  assert.deepEqual(it.covers, ['w:切ります']);
  assert.deepEqual(it.skills, ['單字']);
});

test('選項是決定性的：重跑兩次完全一致', () => {
  const a = [...generate(jpVocab)].find((x) => x.id === 'recall:きります:jp2zh');
  const b = [...generate(jpVocab)].find((x) => x.id === 'recall:きります:jp2zh');
  assert.deepEqual(a.choices, b.choices);
});

test('同課可用詞不足四個時不產生選擇題（寧可不出，也不出兩選一）', () => {
  const few = [
    { kana: 'あ', kanji: null, zh: '甲', lesson: 1, no: 1 },
    { kana: 'い', kanji: null, zh: '乙', lesson: 1, no: 2 },
  ];
  assert.equal([...generate(few)].filter((x) => x.id.endsWith(':jp2zh')).length, 0);
});

test('誘答取自同一課，才不會靠課次差異猜答案', () => {
  const mixed = [...jpVocab, { kana: 'ほん', kanji: '本', zh: '書', lesson: 1, no: 9 }];
  const it = [...generate(mixed)].find((x) => x.id === 'recall:きります:jp2zh');
  assert.ok(!it.choices.includes('書'), '第1課的詞不該成為第7課題目的誘答');
});

test('全語料的 jp2zh 選項都不含正解以外的重複，且正解必在其中', () => {
  const items = [...generate(jpVocab)].filter((x) => x.id.endsWith(':jp2zh'));
  assert.ok(items.length > 0);
  for (const it of items) {
    assert.ok(it.choices.includes(it.answer), `${it.id} 的選項不含正解`);
    assert.equal(new Set(it.choices).size, it.choices.length, `${it.id} 的選項有重複`);
  }
});

test('選項截掉課本的用法說明（長度本身不得成為線索）', () => {
  const withNote = [
    { kana: 'あのひと', kanji: null, zh: '他，她，那個人 （ あの かた ）（“あのかた”是禮貌形）', lesson: 1, no: 1 },
    { kana: 'わたし', kanji: null, zh: '我', lesson: 1, no: 2 },
    { kana: 'せんせい', kanji: '先生', zh: '老師', lesson: 1, no: 3 },
    { kana: 'がくせい', kanji: '学生', zh: '學生', lesson: 1, no: 4 },
    { kana: 'いしゃ', kanji: '医者', zh: '醫生', lesson: 1, no: 5 },
  ];
  const it = [...generate(withNote)].find((x) => x.id === 'recall:あのひと:jp2zh');
  assert.equal(it.answer, '他，她，那個人');
  for (const c of it.choices) assert.ok(!c.includes('（'), `選項夾了用法說明：${c}`);
});

test('整筆都是用法說明時退回原字串，不產生空選項', () => {
  const noteOnly = [
    { kana: 'ちゃん', kanji: null, zh: '（用於小孩的名字後）', lesson: 1, no: 1 },
    { kana: 'わたし', kanji: null, zh: '我', lesson: 1, no: 2 },
    { kana: 'せんせい', kanji: '先生', zh: '老師', lesson: 1, no: 3 },
    { kana: 'がくせい', kanji: '学生', zh: '學生', lesson: 1, no: 4 },
    { kana: 'いしゃ', kanji: '医者', zh: '醫生', lesson: 1, no: 5 },
  ];
  const it = [...generate(noteOnly)].find((x) => x.id === 'recall:ちゃん:jp2zh');
  assert.equal(it.answer, '（用於小孩的名字後）');
  for (const c of it.choices) assert.ok(c.length > 0, '選項不得為空');
});

// zh2jp 的題幹取自 v.zh，是中文。振假名詞典分不出中日文（兩者共用 CJK 漢字區），
// 少了這個標記，「對不起」的「起」會被標成 お。見 tests/app/test_present.js。
test('zh2jp 的題幹標記為中文，呈現端才知道不要加振假名', () => {
  for (const it of [...generate(V)].filter((i) => i.id.endsWith(':zh2jp'))) {
    assert.equal(it.prompt.lang, 'zh', `${it.id} 的題幹是中文卻沒有標記`);
  }
});

test('日文題幹不標成中文（否則會失去振假名）', () => {
  for (const it of [...generate(V)].filter((i) => !i.id.endsWith(':zh2jp'))) {
    assert.notEqual(it.prompt.lang, 'zh', `${it.id} 的題幹是日文，不該標成中文`);
  }
});
