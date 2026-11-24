import { toHiragana, stripSpaces } from '../lang/kana.js';

const FULLWIDTH_OFFSET = 0xfee0; // 全形 ！～～ 對應半形

function toHalfWidth(s) {
  return s.replace(/[！-～]/g, (ch) =>
    String.fromCharCode(ch.charCodeAt(0) - FULLWIDTH_OFFSET));
}

/**
 * 引號只是標示（書名、引用的話、外語），打不打都算對。
 * reading.js 的 prep() 也用這個，兩邊的判分才一致。
 */
export function stripQuotes(s) {
  return s.replace(/[「」『』“”"]/gu, '');
}

export function normalizeAnswer(s) {
  if (typeof s !== 'string') return '';
  let out = toHalfWidth(s);
  out = toHiragana(out);
  out = stripSpaces(out);
  out = stripQuotes(out);
  out = out.replace(/[。.．]+$/u, '');   // 只移除結尾的句號
  return out;
}

export function isCorrect(input, answer, alternatives = []) {
  const got = normalizeAnswer(input);
  if (got.length === 0) return false;
  return [answer, ...alternatives].some((a) => normalizeAnswer(a) === got);
}
