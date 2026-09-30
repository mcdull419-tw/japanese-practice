/**
 * 練習Ｂ（需求 #11 #13）。
 *
 * 與練習Ａ（generators/substitute.js）分開的理由，是兩者的**素材結構不同**，
 * 不是為了多一個引擎：練習Ａ 是代入表（template ＋ slots ＋ rows，機器展開），
 * 練習Ｂ 是變形練習——學生要對提示詞施加一個文法操作（改時態、改否定、
 * 形容詞變化、依はい／いいえ 改極性），操作本身才是考點。
 *
 * 2a 曾照「練習Ｂ 也是代入表」的假設實作，產出的句子約三到五成是錯的日文
 * （「きのう 何を しますか」「忙しいじゃ ありません」「猫が あります」）。
 * 因此 data/drills.json 存的是逐列人工書寫的答案，這裡只負責組成題目。
 *
 * 作答形式仍是打字，沿用 substitute 引擎，不新增第五個引擎（規格 §6.1）。
 */
import { skillOf } from '../core/concepts.js';

export const ENGINE = 'substitute';

export function* generate(drills, patternConcepts) {
  for (const [id, d] of Object.entries(drills || {})) {
    // 概念對應不到時退回以該則 id 當概念，讓這則練習仍然累積熟悉度。
    // 靜默丟棄素材更糟：使用者會發現某些課本練習從來沒出現過。
    const covers = (patternConcepts && patternConcepts.get(id)) || [`g:${id}`];
    const skills = [...new Set(covers.map(skillOf).filter(Boolean))];

    for (const [i, row] of (d.rows || []).entries()) {
      // 答案與範例答案一字不差時略過：題幹印著範例，等於把答案寫在題目上。
      // 這在 ask 型特別容易發生（答句短又定型），課本無妨——紙本是連著做的，
      // 但單獨抽出來當一題就沒有練習價值。
      if (row.answer === d.model_answer) continue;

      // ask 型：題幹本身就是問句，要求的是答句（規格 §13 決定 7 第 4 點）。
      const text = d.ask
        ? `例：${d.model_cue}\n　→ ${d.model_answer}\n\n${row.cue}`
        : `例：${d.model_cue}\n　→ ${d.model_answer}\n\n用這個提示造句：${row.cue}`;

      yield {
        id: `drill:${id}:${i}`,
        engine: ENGINE,
        lesson: d.lesson,
        requires_lesson: d.lesson,
        covers,
        skills,
        prompt: {
          type: 'text',
          text,
          hint: d.ask ? '照範例回答問題' : '照範例的句型造句',
        },
        answer: row.answer,
        alternatives: [],
        source_ref: d.source_ref,
      };
    }
  }
}
