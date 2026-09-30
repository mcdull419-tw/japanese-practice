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

  // 中文題幹不加振假名。中日文共用 CJK 統一漢字區，詞典的最長匹配分不出來，
  // 「對不起」的「起」會被配上 起きます 的 お。題幹語言只有產生器知道，所以
  // 由題目自己宣告——不能在 ruby.js 裡猜，那支是不碰語境的純切詞函式。
  if (item.prompt?.lang === 'zh') {
    return { rubyTokens: text ? [{ t: 'text', s: text }] : [], hideRt };
  }

  const marks = item.source_id && sentenceMarks ? sentenceMarks.get(item.source_id) : null;
  const rubyTokens = marks && marks.length && marksApplyCleanly(text, marks)
    ? annotateWithMarks(text, marks)
    : annotateWithLexicon(text, lex);
  return { rubyTokens, hideRt };
}
