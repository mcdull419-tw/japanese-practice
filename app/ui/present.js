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

/**
 * 以字串（而非位置索引）切出中文段落。索引會因題幹重組而位移——挖空題的教訓
 * 見上方 marksApplyCleanly 的註解。這裡的字串正是產生器自己拼進去的字面值，
 * 對不上就代表題幹變了，該段自然不再被視為中文，不會誤切。
 */
function splitByLiterals(text, literals) {
  let segs = [{ zh: false, s: text }];
  for (const lit of literals) {
    if (!lit) continue;
    const next = [];
    for (const seg of segs) {
      if (seg.zh) { next.push(seg); continue; }
      const parts = seg.s.split(lit);
      parts.forEach((p, i) => {
        if (i > 0) next.push({ zh: true, s: lit });
        if (p) next.push({ zh: false, s: p });
      });
    }
    segs = next;
  }
  return segs;
}

export function presentOptsFor(item, { lex, sentenceMarks }) {
  // hideRuby 讓題目自行宣告「答案就是讀音」。量詞與時刻題的 covers 是 c:<量詞>／
  // 數字概念，歸在「數量」技能是對的，不該為了藏讀音去改 covers——那會讓儀表板
  // 把這些題錯算成「讀音」技能。
  const hideRt = item.prompt?.hideRuby === true
    || (item.covers || []).some((c) => c.endsWith(':reading'));
  const text = item.prompt?.text || '';

  // 中文題幹不加振假名。中日文共用 CJK 統一漢字區，詞典的最長匹配分不出來，
  // 「對不起」的「起」會被配上 起きます 的 お。題幹語言只有產生器知道，所以
  // 由題目自己宣告——不能在 ruby.js 裡猜，那支是不碰語境的純切詞函式。
  if (item.prompt?.lang === 'zh') {
    return { rubyTokens: text ? [{ t: 'text', s: text }] : [], hideRt };
  }

  // 中日混排題幹（練習Ａ／Ｂ）：中文標籤與日文例句同在一個字串裡，只標日文段落。
  const zhParts = item.prompt?.zhParts;
  if (zhParts && zhParts.length) {
    const rubyTokens = [];
    for (const seg of splitByLiterals(text, zhParts)) {
      if (seg.zh) rubyTokens.push({ t: 'text', s: seg.s });
      else rubyTokens.push(...annotateWithLexicon(seg.s, lex));
    }
    return { rubyTokens, hideRt };
  }

  const marks = item.source_id && sentenceMarks ? sentenceMarks.get(item.source_id) : null;
  const rubyTokens = marks && marks.length && marksApplyCleanly(text, marks)
    ? annotateWithMarks(text, marks)
    : annotateWithLexicon(text, lex);
  return { rubyTokens, hideRt };
}
