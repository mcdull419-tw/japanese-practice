import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const drills = JSON.parse(readFileSync(new URL('../../data/drills.json', import.meta.url)));

/**
 * 練習Ｂ 的答案是人工逐句寫的（規格 §13 決定 11）——不是樣板代入的產物，因此
 * 沒有「往返驗證」那種結構性把關可用。這裡的不變式擋的是手寫最容易犯的錯：
 * 整列寫錯行、漏字、殘留樣板記號、標點不合法。語意正確性由使用中的
 * 「這題怪怪的」標記與 data/corrections.json 承接。
 */

const JP_OK = /^[぀-ヿ一-鿿ｦ-ﾟ0-9A-Za-zＡ-Ｚａ-ｚ０-９、。，？！「」『』（）()・～ー 　／\/]+$/;

test('每則都有課次、出處、範例與至少三列', () => {
  for (const [id, d] of Object.entries(drills)) {
    assert.ok(d.lesson >= 1 && d.lesson <= 15, `${id} 的課次異常`);
    assert.match(d.source_ref, /^第\d+課 練習Ｂ-\d+$/, `${id} 的 source_ref 格式異常`);
    assert.ok(d.model_cue && d.model_cue.length > 0, `${id} 缺範例提示`);
    assert.ok(d.model_answer && d.model_answer.length > 0, `${id} 缺範例答案`);
    assert.ok(d.rows.length >= 3, `${id} 只有 ${d.rows.length} 列，太少`);
  }
});

test('每一列都有提示與答案，且答案不是照抄範例', () => {
  for (const [id, d] of Object.entries(drills)) {
    for (const [i, r] of d.rows.entries()) {
      assert.ok(r.cue && r.cue.trim().length > 0, `${id} 第 ${i} 列缺提示`);
      assert.ok(r.answer && r.answer.trim().length > 0, `${id} 第 ${i} 列缺答案`);
      // ask 型（題幹給問句、只要求答句）的答句短且高度定型，「はい、勉強します。」
      // 這種答案與範例相同是正常的，不算缺陷。
      if (!d.ask) {
        assert.notEqual(r.answer, d.model_answer,
          `${id} 第 ${i} 列的答案與範例一模一樣，該列等於沒題目`);
      }
    }
  }
});

test('答案不得殘留樣板記號或草稿欄位', () => {
  for (const [id, d] of Object.entries(drills)) {
    assert.equal(d.template, undefined, `${id} 不該有 template（練習Ｂ 不是代入表）`);
    assert.equal(d.slots, undefined, `${id} 不該有 slots`);
    for (const [i, r] of d.rows.entries()) {
      assert.ok(!/[{}]/.test(r.answer), `${id} 第 ${i} 列的答案殘留樣板記號：${r.answer}`);
    }
  }
});

test('答案只含日文可用字元（抓貼錯內容與控制字元）', () => {
  for (const [id, d] of Object.entries(drills)) {
    for (const [i, r] of d.rows.entries()) {
      assert.match(r.answer, JP_OK, `${id} 第 ${i} 列的答案含非預期字元：${r.answer}`);
    }
  }
});

/**
 * 這條只擋一種錯：**整列寫錯行**（把第 3 列的答案寫到第 2 列去）。手寫 210 句時
 * 這是最可能發生、也最難用眼睛看出來的錯誤——兩句都是通順的日文，只有對照
 * 提示詞才看得出錯位。
 *
 * 判準刻意放寬成「至少一個詞的詞頭出現在答案中」，不逐詞檢查。逐詞檢查會被
 * 正常的詞形變化打敗，而且是各式各樣的打敗法：
 *   帰ります → 帰って（語幹末音也變）
 *   釣りを します → 釣りに 行きます（動詞整個消失）
 *   あさって 働きますか。→ いいえ、働きません。（時間詞不出現在答句）
 * 一條會誤報的檢查最後只會被關掉，比放寬還糟。錯位時連一個詞都對不上，
 * 寬鬆版照樣抓得到。
 */
test('每一列的答案至少含提示詞中一個詞的詞頭（抓整列錯位）', () => {
  for (const [id, d] of Object.entries(drills)) {
    for (const [i, r] of d.rows.entries()) {
      const tokens = r.cue
        .replace(/[（(].*?[）)]/g, ' ')  // 括號內是補充資訊，不一定原樣出現
        .split(/[\s　・／\/、。]+/)
        .filter((s) => s.length >= 1);  // 單字提示（「魚」）也算一個詞
      assert.ok(tokens.length > 0, `${id} 第 ${i} 列的提示切不出任何詞`);
      // 「帰ります → 帰って」這類語幹末音也變的動詞，前兩字對不上，退而求其次
      // 只比對首字——且僅限首字是漢字時，漢字夠獨特，不會像假名那樣一比就中。
      const hit = tokens.some((t) => r.answer.includes(t.slice(0, 2))
        || (/[\u4e00-\u9fff]/.test(t[0]) && r.answer.includes(t[0])));
      assert.ok(hit,
        `${id} 第 ${i} 列可能錯位：提示「${r.cue}」與答案「${r.answer}」沒有任何共同詞頭`);
    }
  }
});

test('id 對得上課本的練習Ｂ', () => {
  const real = new Set();
  for (let n = 1; n <= 15; n++) {
    const d = JSON.parse(readFileSync(
      new URL(`../../data/lessons/${String(n).padStart(2, '0')}.json`, import.meta.url)));
    for (const dr of d.drills || []) real.add(dr.id);
  }
  for (const id of Object.keys(drills)) {
    assert.ok(real.has(id), `${id} 不存在於課本資料中`);
  }
});

test('題數在規格 §13 決定 7 預估的量級（200 ~ 300 題）', () => {
  const total = Object.values(drills).reduce((n, d) => n + d.rows.length, 0);
  assert.ok(total >= 200, `只有 ${total} 題`);
});
