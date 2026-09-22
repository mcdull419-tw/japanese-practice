/**
 * 代入題（需求 #11 句型代入、#13 句型練習）。
 *
 * 素材是課本練習Ａ的代入表：template 帶槽位、slots 給各槽位的候選詞、
 * rows 給出哪些組合是課本列出的合法搭配。逐列展開即可，不自行做笛卡兒積
 * ——課本的 rows 是有意義的配對（日本人配はし、アメリカ人配ナイフ），
 * 全組合會造出「日本人はナイフで」這種課本沒教、也未必自然的句子。
 *
 * 複合題：covers 含句型概念與各槽位填充詞，答錯時全部計入（規格 §7.5 第2點
 * 的已知過度歸因，token 級精準歸因屬 Phase 4）。
 *
 * 語序自由度無法窮舉（規格 §9.2 第四類），由「我這樣寫也對」承接。
 */
import { skillOf } from '../core/concepts.js';

export const ENGINE = 'substitute';

const SLOT = /\{([A-Z])\}/g;

function fillRow(pattern, row) {
  const keys = Object.keys(pattern.slots);
  const values = {};
  for (let i = 0; i < keys.length; i++) {
    const v = pattern.slots[keys[i]][row[i]];
    if (v == null) return null; // 索引越界：課本資料有缺，略過該列而非產生壞題
    values[keys[i]] = v;
  }
  const filled = pattern.template.replace(SLOT, (_, k) => values[k] ?? '');
  // 空字串槽位（課本該列此處不填）不列進提示，否則題幹會出現「あした ／ 」。
  return { filled, values, cues: keys.map((k) => values[k]).filter(Boolean) };
}

export function* generate(patterns, patternConcepts) {
  for (const p of patterns) {
    const rows = p.rows || [];
    // 只有一列的表沒有「代入」可練——那是一個例句，不是代入練習。
    if (rows.length < 2 || !p.template || !p.slots) continue;

    const filledRows = rows.map((r) => fillRow(p, r));
    // 概念對應不到時退回以表 id 當概念，讓這張表的練習仍然累積熟悉度。
    // 靜默丟棄素材才是更糟的結果：使用者會發現某些課本練習從來沒出現過。
    const covers = patternConcepts.get(p.id) || [`g:${p.id}`];
    const skills = [...new Set(covers.map(skillOf).filter(Boolean))];

    for (let i = 0; i < rows.length; i++) {
      const cur = filledRows[i];
      if (!cur) continue;
      // 範例取「另一列」中第一個有效者（通常是第0列；輪到第0列時改用第1列），
      // 範例等於答案的話這題就沒得練了。某列越界失效時順延到下一個有效列，
      // 不讓一列壞資料連帶拖掉別列的題目。
      const example = filledRows.find((r, j) => j !== i && r);
      if (!example) continue;

      yield {
        id: `subst:${p.id}:${i}`,
        engine: ENGINE,
        lesson: p.lesson,
        requires_lesson: p.requires_lesson ?? p.lesson,
        covers,
        skills,
        prompt: {
          type: 'text',
          text: `例：${example.filled}\n用這些詞造句：${cur.cues.join(' ／ ')}`,
          hint: '照範例的句型造句',
        },
        answer: cur.filled,
        alternatives: [],
        source_ref: `第${p.lesson}課 練習Ａ-${p.id.split('-A')[1] || ''}`,
      };
    }
  }
}
