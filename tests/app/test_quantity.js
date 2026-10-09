import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../app/generators/quantity.js';
import { COUNTERS } from '../../app/lang/counters.js';
import { TIMEWORDS } from '../../app/lang/timewords.js';

const items = [...generate()];
const byId = new Map(items.map((it) => [it.id, it]));

test('時刻題：4時 → よじ', () => {
  const it = byId.get('qty:hour:4');
  assert.ok(it, '應有 qty:hour:4');
  assert.equal(it.engine, 'recall');
  assert.equal(it.prompt.text, '4時');
  assert.equal(it.answer, 'よじ');
  assert.deepEqual(it.covers, ['n:time:hour']);
  assert.deepEqual(it.skills, ['數量']);
  assert.equal(it.requires_lesson, 4);
});

test('日期題：20日 → はつか', () => {
  const it = byId.get('qty:day:20');
  assert.ok(it);
  assert.equal(it.answer, 'はつか');
  assert.deepEqual(it.covers, ['n:date:day']);
  assert.equal(it.requires_lesson, 5);
});

test('量詞題：3本 → さんぼん', () => {
  const it = byId.get('qty:c:hon:3');
  assert.ok(it);
  assert.equal(it.prompt.text, '3本');
  assert.equal(it.answer, 'さんぼん');
  assert.deepEqual(it.covers, ['c:hon']);
  assert.equal(it.requires_lesson, 11);
});

test('樓層與次數雖同為かい，但各自獨立成題', () => {
  assert.equal(byId.get('qty:c:kai_floor:3').answer, 'さんがい');
  assert.equal(byId.get('qty:c:kai_times:3').answer, 'さんかい');
  assert.notEqual(byId.get('qty:c:kai_floor:3').covers[0], byId.get('qty:c:kai_times:3').covers[0]);
});

test('全部 id 唯一且決定性（重跑兩次結果相同）', () => {
  const ids = items.map((it) => it.id);
  assert.equal(new Set(ids).size, ids.length, '不得有重複 id');
  const again = [...generate()].map((it) => it.id);
  assert.deepEqual(again, ids, '同一份規則重跑必須得到同一組 id');
});

test('每題欄位齊備', () => {
  for (const it of items) {
    assert.equal(typeof it.id, 'string');
    assert.equal(it.engine, 'recall');
    assert.ok(Array.isArray(it.covers) && it.covers.length > 0, `${it.id} 缺 covers`);
    assert.ok(it.answer.length > 0, `${it.id} 缺答案`);
    assert.ok(it.source_ref.length > 0, `${it.id} 缺出處`);
    assert.ok(it.requires_lesson >= 1 && it.requires_lesson <= 15, `${it.id} 的 requires_lesson 異常`);
    assert.ok(it.lesson >= 1 && it.lesson <= 15, `${it.id} 的 lesson 異常`);
  }
});

test('題數與資料表大小相符', () => {
  // 時12 ＋ 分14 ＋ 日31 ＋ 月12 ＝ 69；疑問詞 4、半 1、零 1；百千音變 14、萬億 5、小數 2、分數 2；
  // 時間詞每列一題；量詞每種 1~10 加疑問詞 ＝ 11 題（つ 與 円 沒有疑問詞題，少 2；円不在補充講義）
  const expected = 69 + 4 + 1 + 1 + 14 + 5 + 2 + 2 + TIMEWORDS.length
    + Object.keys(COUNTERS).length * 11 - 2 + 1; // +1：半年
  assert.equal(items.length, expected);
});

// 這些題目問的就是唸法，答案是讀音。振假名若照常顯示，等於把答案印在題幹上
// （「4時」標著「時→じ」）。covers 用的是 c:<量詞>／數字概念而非 :reading 後綴——
// 那個歸類是對的（屬「數量」技能），所以改由題目宣告，不動 covers。
test('所有量詞與數字題都藏住振假名（否則答案寫在題目上）', () => {
  for (const it of items) {
    assert.equal(it.prompt.hideRuby, true, `${it.id}（${it.prompt.hint}）沒有宣告藏振假名`);
  }
});

test('新增量詞出題：1つ → ひとつ、3個 → さんこ', () => {
  assert.equal(byId.get('qty:c:tsu:1').answer, 'ひとつ');
  assert.equal(byId.get('qty:c:tsu:1').prompt.text, '1つ');
  assert.equal(byId.get('qty:c:ko:3').answer, 'さんこ');
});

test('17日、27日 出題且唸しち；19日 唸く', () => {
  assert.equal(byId.get('qty:day:17').answer, 'じゅうしちにち');
  assert.equal(byId.get('qty:day:27').answer, 'にじゅうしちにち');
  assert.equal(byId.get('qty:day:19').answer, 'じゅうくにち');
});

test('期間題與日期題的題幹可分辨：1日（ついたち）vs 1日（天數）（いちにち）', () => {
  assert.equal(byId.get('qty:day:1').prompt.text, '1日');
  assert.equal(byId.get('qty:day:1').answer, 'ついたち');
  assert.equal(byId.get('qty:c:nichi_span:1').prompt.text, '1日（天數）');
  assert.equal(byId.get('qty:c:nichi_span:1').answer, 'いちにち');
  // 「2日間」是ふつかかん，講義的欄位是「天」（2日＝ふつか），不能把題幹寫成日間。
  assert.ok(![...byId.values()].some((it) => /日間/.test(it.prompt.text)), '題幹不得出現日間');
});

test('「つ」的 10 是とお：題幹不寫成「10つ」（沒有這種寫法）', () => {
  assert.equal(byId.get('qty:c:tsu:10').answer, 'とお');
  assert.notEqual(byId.get('qty:c:tsu:10').prompt.text, '10つ');
});

test('並列讀法進 alternatives：10分 じっぷん、7人 しちにん、10本 じっぽん 也算對', () => {
  const m = byId.get('qty:minute:10');
  assert.equal(m.answer, 'じゅっぷん');
  assert.ok(m.alternatives.includes('じっぷん'));
  assert.ok(byId.get('qty:c:nin:7').alternatives.includes('しちにん'));
  assert.ok(byId.get('qty:c:hon:10').alternatives.includes('じっぽん'));
});

test('疑問詞題：何本 → なんぼん；何時 → なんじ', () => {
  const it = byId.get('qty:c:hon:q');
  assert.equal(it.prompt.text, '何本');
  assert.equal(it.answer, 'なんぼん');
  assert.equal(byId.get('qty:hour:q').answer, 'なんじ');
  assert.equal(byId.get('qty:day:q').prompt.text, '何日');
});

test('「つ」沒有疑問詞題（題幹與答案相同，沒有意義）', () => {
  assert.equal(byId.has('qty:c:tsu:q'), false);
});

test('萬、億、小數、分數、零、百千音變題', () => {
  assert.equal(byId.get('qty:big:10000').answer, 'いちまん');
  assert.equal(byId.get('qty:big:100000000').answer, 'いちおく');
  assert.equal(byId.get('qty:dec:17.5').answer, 'じゅうななてんご');
  assert.equal(byId.get('qty:frac:1/2').answer, 'にぶんのいち');
  assert.equal(byId.get('qty:zero').answer, 'ゼロ');
  assert.ok(byId.get('qty:zero').alternatives.includes('れい'));
  assert.equal(byId.get('qty:num:600').answer, 'ろっぴゃく');
  assert.ok(byId.get('qty:num:17').alternatives.includes('じゅうしち'));
});

test('時間詞題：前天 → おととい，歸入數量技能，昨晚的ゆうべ也算對', () => {
  const it = byId.get('qty:tw:day:-2');
  assert.equal(it.prompt.text, '前天');
  assert.equal(it.answer, 'おととい');
  assert.deepEqual(it.skills, ['數量']);
  assert.ok(byId.get('qty:tw:evening:-1').alternatives.includes('ゆうべ'));
});

test('既有 id 不變（作答紀錄靠 id 對應）', () => {
  for (const id of ['qty:hour:4', 'qty:minute:10', 'qty:day:20', 'qty:month:4', 'qty:c:hon:3', 'qty:c:kai_floor:3']) {
    assert.ok(byId.has(id), `既有題目 ${id} 不見了`);
  }
});

test('同一題幹不會有兩種不同的正解（避免出題自相矛盾）', () => {
  const seen = new Map();
  for (const it of items) {
    const key = `${it.prompt.text}`;
    const prev = seen.get(key);
    if (prev && prev.answer !== it.answer) {
      assert.fail(`題幹 ${key} 同時是 ${prev.id}(${prev.answer}) 與 ${it.id}(${it.answer})`);
    }
    seen.set(key, it);
  }
});

test('6か月 與 半年 分開出題：はんとし 不是 6か月 的讀音', () => {
  assert.deepEqual(byId.get('qty:c:kagetsu:6').alternatives, []);
  assert.equal(byId.get('qty:c:kagetsu:half').prompt.text, '半年');
  assert.equal(byId.get('qty:c:kagetsu:half').answer, 'はんとし');
});
