/**
 * 「看提示」顯示的文字。純函式，不碰 DOM。
 *
 * 提示原本是「題型說明（開頭：答案第一個字）」。答案以漢字開頭時，那個漢字
 * 多半就印在題幹上（食べます → て形，開頭：食），等於沒提示。改成給該字的
 * 讀音第一個假名——讀音才是使用者卡住的地方。
 */
import { annotateWithLexicon } from './ruby.js';

const KANJI = /[\u4e00-\u9fff々]/;

// 詞典刻意不收「何」：なに／なん 依後字而定，收了會讓振假名標錯（何週間）。
// 提示只要第一個假名，兩種唸法都是な，在這裡補即可。
const HEAD_KANA = { 何: 'な' };

/**
 * 答案開頭的提示字。漢字開頭時取讀音的第一個假名：產生器知道讀音的（動詞、
 * 形容詞、填空題）會帶 answerKana，優先用它；否則查詞典。都查不到就回傳
 * null——寧可不給，也不給一個題幹上就看得到的漢字。
 */
export function answerHead(answer, lex, answerKana) {
  const first = (answer || '').slice(0, 1);
  if (!first) return null;
  if (!KANJI.test(first)) return first;
  if (answerKana) return answerKana.slice(0, 1);
  if (HEAD_KANA[first]) return HEAD_KANA[first];
  const tok = annotateWithLexicon(answer, lex || new Map())[0];
  if (tok && tok.t === 'ruby' && tok.kana) return tok.kana.slice(0, 1);
  return null;
}

export function hintText(item, lex) {
  const base = item.prompt?.hint || '';
  const head = answerHead(item.answer, lex, item.answerKana);
  return head ? `${base}（開頭：${head}）` : base;
}
