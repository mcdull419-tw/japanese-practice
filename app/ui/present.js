/**
 * 呈現修飾的決策點（規格 §9.3）：這一題的題幹要不要加振假名、要不要藏讀音。
 *
 * hideRt 由 covers 判定而非使用者設定——考讀音的題型若顯示 rt，答案就直接
 * 寫在題目上。規格明定此判斷不可由設定控制，避免使用者誤開後題目失效。
 */
import { annotateWithMarks, annotateWithLexicon } from '../core/ruby.js';

/**
 * 課本標註全部對得上才用標註，否則整句改走詞典。
 *
 * 「部分對得上就用部分」看似寬容，實際更糟：挖空題的題幹是原句挖掉助詞後的
 * 產物，後半段每個 at 都位移了——那會變成前半有振假名、後半沒有，而且沒有
 * 任何跡象顯示是位移造成的。整句退回詞典至少是一致的結果。
 */
function marksApplyCleanly(text, marks) {
  return marks.every((m) => text.slice(m.at, m.at + (m.base || '').length) === m.base);
}

export function presentOptsFor(item, { lex, sentenceMarks }) {
  const hideRt = (item.covers || []).some((c) => c.endsWith(':reading'));
  const text = item.prompt?.text || '';
  const marks = item.source_id && sentenceMarks ? sentenceMarks.get(item.source_id) : null;
  const rubyTokens = marks && marks.length && marksApplyCleanly(text, marks)
    ? annotateWithMarks(text, marks)
    : annotateWithLexicon(text, lex);
  return { rubyTokens, hideRt };
}
