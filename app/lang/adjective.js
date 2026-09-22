/**
 * い／な 形容詞變化。鏡射 lang/conjugation.js 的形狀（FORMS／FORM_LESSON／單一變化函式）。
 *
 * 回傳完整的禮貌形（含です／じゃありません），不是語幹——課本操練的是
 * 「大きくないです」這個完整形式，使用者要打的也是它，與 conjugate() 回傳
 * 完整ます形一致。
 *
 * て形與副詞形課本第16課才教，超出本專案1~15課的範圍。仍然寫完整，由
 * FORM_LESSON 的 16 擋在範圍之外（同 conjugation.js 收錄可能形的作法）：
 * 日後擴充課次範圍時不需要改程式。
 */
export const FORMS = ['plain', 'neg', 'past', 'pastneg', 'te', 'adverb'];

/** 各形態在課本中首次出現的課次（已核對 L08／L12 的 grammar 標題）。 */
export const FORM_LESSON = { plain: 8, neg: 8, past: 12, pastneg: 12, te: 16, adverb: 16 };

const I_SUFFIX = { plain: 'いです', neg: 'くないです', past: 'かったです',
  pastneg: 'くなかったです', te: 'くて', adverb: 'く' };

const NA_SUFFIX = { plain: 'です', neg: 'じゃありません', past: 'でした',
  pastneg: 'じゃありませんでした', te: 'で', adverb: 'に' };

const I_ALT = { neg: 'くありません', pastneg: 'くありませんでした' };
const NA_ALT = { neg: 'ではありません', pastneg: 'ではありませんでした' };

/**
 * いい 的不規則：除了 plain 之外一律改用 よ 語幹（よかった／よくない）。
 * かっこいい、きもちいい 這類複合詞同樣只有末尾的いい 變化，因此比對的是
 * 「以いい結尾」而非「等於いい」。
 */
function iStem(citation) {
  if (citation.endsWith('いい')) return citation.slice(0, -2) + 'よ';
  return citation.slice(0, -1);
}

function check(citation, type, form) {
  if (typeof citation !== 'string' || citation.length === 0) {
    throw new Error(`adjective: 需要非空字串，收到 ${JSON.stringify(citation)}`);
  }
  if (type !== 'i' && type !== 'na') {
    throw new Error(`adjective: 未知的 type ${JSON.stringify(type)}`);
  }
  if (!FORMS.includes(form)) {
    throw new Error(`adjective: 未知的 form ${JSON.stringify(form)}`);
  }
  if (type === 'i' && !citation.endsWith('い')) {
    throw new Error(`adjective: い形容詞須以い結尾，收到 ${JSON.stringify(citation)}`);
  }
}

export function conjugateAdj(citation, type, form) {
  check(citation, type, form);
  if (type === 'na') return citation + NA_SUFFIX[form];
  // plain 不套 よ 語幹：いい 的現在肯定就是「いいです」，不是「よいです」。
  if (form === 'plain') return citation + 'です';
  return iStem(citation) + I_SUFFIX[form];
}

export function conjugateAdjAlts(citation, type, form) {
  check(citation, type, form);
  const table = type === 'na' ? NA_ALT : I_ALT;
  const suffix = table[form];
  if (!suffix) return [];
  if (type === 'na') return [citation + suffix];
  return [iStem(citation) + suffix];
}
