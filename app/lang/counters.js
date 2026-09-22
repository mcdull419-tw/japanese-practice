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
  en:        { kana: 'えん', label: '円', lesson: 3,  table: withNumberOverrides('えん', { 4: 'よ' }) },
  jikan:     { kana: 'じかん', label: '時間', lesson: 11,
               table: withNumberOverrides('じかん', { 4: 'よ', 7: 'しち', 9: 'く' }) },
  nen:       { kana: 'ねん', label: '年', lesson: 11, table: withNumberOverrides('ねん', { 4: 'よ' }) },
};

export function readCounter(n, key) {
  const c = COUNTERS[key];
  if (!c) throw new Error(`readCounter: 未知的量詞 ${JSON.stringify(key)}`);
  if (!Number.isInteger(n) || n < 1 || n > 10) {
    throw new Error(`readCounter: 需要 1~10 的整數，收到 ${JSON.stringify(n)}`);
  }
  if (!c.table) return readNumber(n) + c.kana;
  return c.table[n];
}
