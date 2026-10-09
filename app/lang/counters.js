/**
 * 量詞音變（規格 §6.5）。課本第1、3、4、5、11課陸續教到，各自的解鎖課次
 * 記在 COUNTERS[].lesson，供生成器算 requires_lesson。
 *
 * 音變一律以 1~10 的明表列出，不寫成「規則＋例外」：日語量詞的音變
 * 由數字與量詞首音共同決定（ほん→ぽん／ぼん、ひき→ぴき／びき、
 * かい→がい），交互作用多，明表才不會漏。每個量詞只有10個值，成本很低。
 */
import { readNumber } from './numbers.js';

const H_SERIES = (base, p, b) => ({
  1: `いっ${p}`, 2: `に${base}`, 3: `さん${b}`, 4: `よん${base}`, 5: `ご${base}`,
  6: `ろっ${p}`, 7: `なな${base}`, 8: `はっ${p}`, 9: `きゅう${base}`, 10: `じゅっ${p}`,
});

const K_SERIES = (base, g) => ({
  1: `いっ${base}`, 2: `に${base}`, 3: `さん${g}`, 4: `よん${base}`, 5: `ご${base}`,
  6: `ろっ${base}`, 7: `なな${base}`, 8: `はっ${base}`, 9: `きゅう${base}`, 10: `じゅっ${base}`,
});

const S_SERIES = (base) => ({
  1: `いっ${base}`, 2: `に${base}`, 3: `さん${base}`, 4: `よん${base}`, 5: `ご${base}`,
  6: `ろく${base}`, 7: `なな${base}`, 8: `はっ${base}`, 9: `きゅう${base}`, 10: `じゅっ${base}`,
});

/**
 * 數字本身的讀法隨量詞而變：4 在 えん／ねん／じかん 前讀 よ（不是よん），
 * じかん 的 7 9 與時刻同讀 しち／く。這些量詞的量詞部分不變，變的是數字，
 * 因此以「數字讀法覆寫」表達，其餘位置照 readNumber。
 */
const withNumberOverrides = (base, overrides) => Object.fromEntries(
  Array.from({ length: 10 }, (_, i) => i + 1)
    .map((n) => [n, (overrides[n] || readNumber(n)) + base]));

/** 無音變者：直接用 readNumber 接上量詞。 */
const PLAIN = null;

export const COUNTERS = {
  hon:       { kana: 'ほん', label: '本', lesson: 11, table: H_SERIES('ほん', 'ぽん', 'ぼん') },
  hiki:      { kana: 'ひき', label: '匹', lesson: 11, table: H_SERIES('ひき', 'ぴき', 'びき') },
  satsu:     { kana: 'さつ', label: '冊', lesson: 11, table: S_SERIES('さつ') },
  sai:       { kana: 'さい', label: '歳', lesson: 1,  table: S_SERIES('さい') },
  kai_floor: { kana: 'かい', label: '階', lesson: 3,  table: K_SERIES('かい', 'がい') },
  // 次數與樓層只差在 3：さんかい（回）／さんがい（階）。6 兩者都是ろっかい。
  kai_times: { kana: 'かい', label: '回', lesson: 11, table: K_SERIES('かい', 'かい') },
  nin:       { kana: 'にん', label: '人', lesson: 11,
               table: { 1: 'ひとり', 2: 'ふたり', 3: 'さんにん', 4: 'よにん', 5: 'ごにん',
                        6: 'ろくにん', 7: 'ななにん', 8: 'はちにん', 9: 'きゅうにん', 10: 'じゅうにん' } },
  mai:       { kana: 'まい', label: '枚', lesson: 11, table: PLAIN },
  dai:       { kana: 'だい', label: '台', lesson: 11, table: PLAIN },
  // 補充講義第 IV 節（IMAG0809）新增的量詞。lesson 取課本詞彙表第一次教到的課次；
  // 第 1~15 課詞彙裡找不到者（個、足、軒、杯、着）暫排 15，待確認課本實際教到哪一課。
  // 10 是とお，沒有「10つ」這種寫法，題幹只寫 10。
  tsu:       { kana: 'つ', label: 'つ', prompts: { 10: '10' }, lesson: 11,
               table: { 1: 'ひとつ', 2: 'ふたつ', 3: 'みっつ', 4: 'よっつ', 5: 'いつつ',
                        6: 'むっつ', 7: 'ななつ', 8: 'やっつ', 9: 'ここのつ', 10: 'とお' } },
  ban:       { kana: 'ばん', label: '番', lesson: 4, table: PLAIN },
  chaku:     { kana: 'ちゃく', label: '着', lesson: 15, table: S_SERIES('ちゃく') },
  ko:        { kana: 'こ', label: '個', lesson: 15, table: K_SERIES('こ', 'こ') },
  // 足：3 が ぞく（さんぞく）、6 は ろく（ろっ にならない）。K_SERIES とも S_SERIES とも違うので明表。
  soku:      { kana: 'そく', label: '足', lesson: 15,
               table: { 1: 'いっそく', 2: 'にそく', 3: 'さんぞく', 4: 'よんそく', 5: 'ごそく',
                        6: 'ろくそく', 7: 'ななそく', 8: 'はっそく', 9: 'きゅうそく', 10: 'じゅっそく' } },
  ken:       { kana: 'けん', label: '軒', lesson: 15, table: K_SERIES('けん', 'げん') },
  hai:       { kana: 'はい', label: '杯', lesson: 15, table: H_SERIES('はい', 'ぱい', 'ばい') },
  en:        { kana: 'えん', label: '円', lesson: 3,  table: withNumberOverrides('えん', { 4: 'よ' }) },
  // 7 時間：講義第一讀法是ななじかん，しちじかん 是並列（alts）。9 時間只有くじかん。
  jikan:     { kana: 'じかん', label: '時間', lesson: 11,
               table: withNumberOverrides('じかん', { 4: 'よ', 9: 'く' }),
               alts: { 7: ['しちじかん'] }, q: 'なんじかん' },
  nen:       { kana: 'ねん', label: '年', lesson: 11, table: withNumberOverrides('ねん', { 4: 'よ' }),
               alts: { 7: ['しちねん'], 9: ['くねん'] }, q: 'なんねん' },
  // 期間的日數：1 日是いちにち，與日期的ついたち不同；2~10 與日期同讀。
  nichi_span: { kana: 'にち', label: '日', promptNote: '（天數）', lesson: 5,
                table: { 1: 'いちにち', 2: 'ふつか', 3: 'みっか', 4: 'よっか', 5: 'いつか',
                         6: 'むいか', 7: 'なのか', 8: 'ようか', 9: 'ここのか', 10: 'とおか' },
                q: 'なんにち' },
  shuukan:   { kana: 'しゅうかん', label: '週間', lesson: 11,
               table: { 1: 'いっしゅうかん', 2: 'にしゅうかん', 3: 'さんしゅうかん', 4: 'よんしゅうかん',
                        5: 'ごしゅうかん', 6: 'ろくしゅうかん', 7: 'ななしゅうかん', 8: 'はっしゅうかん',
                        9: 'きゅうしゅうかん', 10: 'じゅっしゅうかん' },
               alts: { 7: ['しちしゅうかん'], 10: ['じっしゅうかん'] }, q: 'なんしゅうかん' },
  kagetsu:   { kana: 'かげつ', label: 'か月', lesson: 11,
               table: { 1: 'いっかげつ', 2: 'にかげつ', 3: 'さんかげつ', 4: 'よんかげつ', 5: 'ごかげつ',
                        6: 'ろっかげつ', 7: 'ななかげつ', 8: 'はちかげつ', 9: 'きゅうかげつ', 10: 'じゅっかげつ' },
               alts: { 6: ['はんとし'], 7: ['しちかげつ'], 8: ['はっかげつ'], 10: ['じっかげつ'] },
               q: 'なんかげつ' },
};

/**
 * 疑問詞（何＋量詞）。連濁（なんぼん、なんびき、なんがい、なんぞく、なんげん、なんばい）
 * 沒有規律可推，直接列明表。時間類（じかん、ねん、…）的 q 已寫在各自條目裡。
 */
const COUNTER_Q = {
  tsu: 'いくつ', nin: 'なんにん', ban: 'なんばん', mai: 'なんまい', dai: 'なんだい',
  sai: 'なんさい', satsu: 'なんさつ', chaku: 'なんちゃく', kai_times: 'なんかい', ko: 'なんこ',
  soku: 'なんぞく', ken: 'なんげん', kai_floor: 'なんがい', hon: 'なんぼん', hai: 'なんばい',
  hiki: 'なんびき',
};

for (const [key, q] of Object.entries(COUNTER_Q)) COUNTERS[key].q = q;

// 講義 10 的並列讀法：じゅっ… 與 じっ… 都對（本、歳、冊、着、回、個、足、軒、階、杯、匹）。
for (const c of Object.values(COUNTERS)) {
  const ten = c.table && c.table[10];
  if (ten && ten.startsWith('じゅっ') && !(c.alts && c.alts[10])) {
    c.alts = { ...c.alts, 10: ['じっ' + ten.slice(3)] };
  }
}
// 人：7 人 ななにん／しちにん 都對。
COUNTERS.nin.alts = { 7: ['しちにん'] };

export function readCounter(n, key) {
  const c = COUNTERS[key];
  if (!c) throw new Error(`readCounter: 未知的量詞 ${JSON.stringify(key)}`);
  if (!Number.isInteger(n) || n < 1 || n > 10) {
    throw new Error(`readCounter: 需要 1~10 的整數，收到 ${JSON.stringify(n)}`);
  }
  if (!c.table) return readNumber(n) + c.kana;
  return c.table[n];
}

/** 講義同格列出的其他讀法（第一讀法以外）。沒有則回空陣列。 */
export function readCounterAlts(n, key) {
  const c = COUNTERS[key];
  if (!c) throw new Error(`readCounterAlts: 未知的量詞 ${JSON.stringify(key)}`);
  return (c.alts && c.alts[n]) || [];
}

/** 疑問詞（何＋量詞）。連濁等不規則直接列明表。 */
export function readCounterQ(key) {
  const c = COUNTERS[key];
  if (!c || !c.q) throw new Error(`readCounterQ: ${JSON.stringify(key)} 沒有疑問詞`);
  return c.q;
}
