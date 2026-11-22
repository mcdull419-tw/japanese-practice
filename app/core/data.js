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
const COLUMN_PAD = /\s{5,}(.*)$/s;
const LEADING_DOT = /^．/;
// 「［お］てら. ［お］」「［お］くに ［お］」：漢字欄的「［お］」掉進假名欄尾巴。
const TRAILING_BRACKET = /\.?\s*(［[^］]+］)$/;
const TRAILING_DOT = /\.$/;

/**
 * 3. 長空白後面接的那段，多半是漢字欄被切掉的開頭（「おねえさん      お」＋「姉さん」
 *    原本是「お姉さん」，「このあいだ      この」＋「間」是「この間」）。漢字欄存在時把它接回去；
 *    漢字欄空的（「とお      10つ」）不接——那段不是漢字寫法。
 * 4. 假名欄尾巴的「［お］」與句點：「［お］てら. ［お］」＋「寺」→「［お］てら」＋「［お］寺」。
 */
export function cleanVocab(v) {
  const out = { ...v };
  let prefix = '';
  if (typeof out.kana === 'string') {
    let k = out.kana;
    const pad = k.match(COLUMN_PAD);
    if (pad) { prefix = pad[1].trim(); k = k.slice(0, pad.index); }
    k = k.replace(LEADING_DOT, '').trim();
    const br = k.match(TRAILING_BRACKET);
    if (br && k.startsWith(br[1]) && k.length > br[0].length) {
      k = k.slice(0, br.index).trim();
      if (!prefix) prefix = br[1];
    }
    out.kana = k.replace(TRAILING_DOT, '').trim();
  }
  if (typeof out.kanji === 'string') {
    let j = out.kanji.replace(COLUMN_PAD, '').replace(LEADING_DOT, '').trim();
    if (prefix && prefix.length <= 4 && !j.startsWith(prefix)) j = prefix + j;
    out.kanji = j;
  }
  return out;
}

/**
 * 逐筆人工更正（data/vocab-fixes.json）：抽取把欄位切錯、或課本版面讓某欄跑到下一行的
 * 少數詞條。以「課次＋原始假名或漢字」比對，避免依賴陣列位置。
 */
export function applyVocabFixes(v, lesson, fixes) {
  for (const f of fixes || []) {
    if (f.lesson !== lesson) continue;
    if (Object.entries(f.match).every(([k, val]) => v[k] === val)) return { ...v, ...f.set };
  }
  return v;
}

/** 代入表的人工更正（data/pattern-fixes.json）。skip 的表整張不用。 */
export function applyPatternFix(p, fixes) {
  const f = fixes && fixes[p.id];
  if (!f) return p;
  if (f.skip) return null;
  return { ...p, ...f };
}

export function buildIndex(lessonsMap, vocabFixes = [], patternFixes = {}) {
  const vocab = [];
  const sentences = [];
  const patterns = [];
  const drills = [];
  for (const [n, data] of [...lessonsMap.entries()].sort((a, b) => a[0] - b[0])) {
    for (const v of data.vocab || []) {
      vocab.push({ ...cleanVocab(applyVocabFixes(v, n, vocabFixes)), lesson: n });
    }
    for (const s of data.sentences || []) sentences.push({ ...s, lesson: n });
    for (const p of data.patterns || []) {
      const fixed = applyPatternFix(p, patternFixes);
      if (fixed) patterns.push({ ...fixed, lesson: n });
    }
    for (const d of data.drills || []) drills.push({ ...d, lesson: n });
  }
  return { vocab, sentences, patterns, drills };
}
