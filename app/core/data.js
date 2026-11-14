/**
 * 載入 Phase 0 產出的課次 JSON 並建立索引。
 * loader 以注入方式提供，讓瀏覽器（fetch）與 Node 測試（fs）共用同一份邏輯。
 */
export async function loadLessons(lessonNumbers, loader) {
  const out = new Map();
  for (const n of lessonNumbers) {
    out.set(n, await loader(n));
  }
  return out;
}

/**
 * 抽取殘留的清洗。PDF 表格抽出來的假名欄有兩種雜質：
 *   1. 欄位對齊用的長空白，後面接著別欄的內容（「ふたり      2」「おねえさん      お」）。
 *      詞組內的正常分隔只有兩個空白，所以門檻訂 5 個——第 11 課那批都在 18 個以上。
 *   2. 前綴的「．」（「．せまい」），課本的記號，不是字的一部分。
 * 不清的話，使用者得連空白與數字一起打才算對。
 *
 * 在載入時清而不改資料檔：抽取程式重跑時資料檔會被整份覆寫。
 */
const COLUMN_PAD = /\s{5,}.*$/s;
const LEADING_DOT = /^．/;

export function cleanVocab(v) {
  const out = { ...v };
  if (typeof out.kana === 'string') {
    out.kana = out.kana.replace(COLUMN_PAD, '').replace(LEADING_DOT, '').trim();
  }
  if (typeof out.kanji === 'string') {
    out.kanji = out.kanji.replace(COLUMN_PAD, '').replace(LEADING_DOT, '').trim();
  }
  return out;
}

export function buildIndex(lessonsMap) {
  const vocab = [];
  const sentences = [];
  const patterns = [];
  const drills = [];
  for (const [n, data] of [...lessonsMap.entries()].sort((a, b) => a[0] - b[0])) {
    for (const v of data.vocab || []) vocab.push({ ...cleanVocab(v), lesson: n });
    for (const s of data.sentences || []) sentences.push({ ...s, lesson: n });
    for (const p of data.patterns || []) patterns.push({ ...p, lesson: n });
    for (const d of data.drills || []) drills.push({ ...d, lesson: n });
  }
  return { vocab, sentences, patterns, drills };
}
