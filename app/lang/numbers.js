/**
 * 數字、時刻、日期、月份的讀音（規格 §6.5）。
 *
 * 本模組的價值全在不規則：よじ 不是しじ、はつか 不是にじゅうよっか、
 * ついたち、ようか、いっぷん／さんぷん。規則部分反而是陪襯。
 * 因此不規則一律以明表列出，不試圖用「規則加例外修補」的寫法表達——
 * 那種寫法在這個領域裡每次擴充都會漏。
 */
const ONES = ['', 'いち', 'に', 'さん', 'よん', 'ご', 'ろく', 'なな', 'はち', 'きゅう'];
const HUNDREDS = ['', 'ひゃく', 'にひゃく', 'さんびゃく', 'よんひゃく', 'ごひゃく',
  'ろっぴゃく', 'ななひゃく', 'はっぴゃく', 'きゅうひゃく'];
const THOUSANDS = ['', 'せん', 'にせん', 'さんぜん', 'よんせん', 'ごせん',
  'ろくせん', 'ななせん', 'はっせん', 'きゅうせん'];

function need(n, lo, hi, what) {
  if (!Number.isInteger(n) || n < lo || n > hi) {
    throw new Error(`${what}: 需要 ${lo}~${hi} 的整數，收到 ${JSON.stringify(n)}`);
  }
}

export function readNumber(n) {
  need(n, 1, 9999, 'readNumber');
  const th = Math.floor(n / 1000);
  const hu = Math.floor((n % 1000) / 100);
  const te = Math.floor((n % 100) / 10);
  const on = n % 10;
  let out = THOUSANDS[th] + HUNDREDS[hu];
  if (te === 1) out += 'じゅう';
  else if (te > 1) out += ONES[te] + 'じゅう';
  out += ONES[on];
  return out;
}

const HOUR_IRREGULAR = { 4: 'よじ', 7: 'しちじ', 9: 'くじ' };

export function readHour(h) {
  need(h, 1, 12, 'readHour');
  return HOUR_IRREGULAR[h] || readNumber(h) + 'じ';
}

/** 分的音變只由個位決定（30分＝さんじゅっぷん，跟10分同型）。 */
const MINUTE_ONES = {
  1: 'いっぷん', 2: 'にふん', 3: 'さんぷん', 4: 'よんぷん', 5: 'ごふん',
  6: 'ろっぷん', 7: 'ななふん', 8: 'はっぷん', 9: 'きゅうふん', 0: 'じゅっぷん',
};

export function readMinute(m) {
  need(m, 1, 59, 'readMinute');
  const te = Math.floor(m / 10);
  const on = m % 10;
  const tens = te === 0 ? '' : (te === 1 ? 'じゅう' : ONES[te] + 'じゅう');
  if (on === 0) {
    // 10、20…50：音變落在「じゅっぷん」上，十位單獨讀
    return (te === 1 ? '' : ONES[te]) + MINUTE_ONES[0];
  }
  return tens + MINUTE_ONES[on];
}

const DAY_IRREGULAR = {
  1: 'ついたち', 2: 'ふつか', 3: 'みっか', 4: 'よっか', 5: 'いつか',
  6: 'むいか', 7: 'なのか', 8: 'ようか', 9: 'ここのか', 10: 'とおか',
  14: 'じゅうよっか', 20: 'はつか', 24: 'にじゅうよっか',
  // 7 と 9 は日付では しち／く（readNumber の なな／きゅう ではない）。補充講義で判明。
  17: 'じゅうしちにち', 19: 'じゅうくにち', 27: 'にじゅうしちにち', 29: 'にじゅうくにち',
};

export function readDayOfMonth(d) {
  need(d, 1, 31, 'readDayOfMonth');
  return DAY_IRREGULAR[d] || readNumber(d) + 'にち';
}

const MONTH_IRREGULAR = { 4: 'しがつ', 7: 'しちがつ', 9: 'くがつ' };

export function readMonth(m) {
  need(m, 1, 12, 'readMonth');
  return MONTH_IRREGULAR[m] || readNumber(m) + 'がつ';
}

/** 0 有兩種讀法，講義第一個是ゼロ。 */
export function readZero() {
  return ['ゼロ', 'れい'];
}

/**
 * 一萬以上。位值只有「萬」「億」兩個，其餘用 readNumber（<10000）接上去：
 * 10000 いちまん（萬位的 1 要唸出來，不像百、千可省）、100000 じゅうまん、
 * 1000000 ひゃくまん、10000000 せんまん、100000000 いちおく。
 */
export function readBig(n) {
  need(n, 10000, 999999999, 'readBig');
  if (n >= 100000000) {
    const o = Math.floor(n / 100000000);
    const rest = n % 100000000;
    return readNumber(o) + 'おく' + (rest ? readBig(rest) : '');
  }
  const m = Math.floor(n / 10000);
  const rest = n % 10000;
  return readNumber(m) + 'まん' + (rest ? readNumber(rest) : '');
}

const DIGIT_KANA = ['れい', 'いち', 'に', 'さん', 'よん', 'ご', 'ろく', 'なな', 'はち', 'きゅう'];

/** 小數：整數部 + てん + 逐位數字（17.5 → じゅうななてんご）。整數部為 0 讀れい。 */
export function readDecimal(str) {
  const [i, f] = String(str).split('.');
  if (!/^\d+$/.test(i) || !/^\d+$/.test(f || '')) {
    throw new Error(`readDecimal: 不是小數 ${JSON.stringify(str)}`);
  }
  const head = Number(i) === 0 ? 'れい' : readNumber(Number(i));
  return head + 'てん' + [...f].map((c) => DIGIT_KANA[Number(c)]).join('');
}

/** 分數：分母＋ぶんの＋分子（1/2 → にぶんのいち）。 */
export function readFraction(num, den) {
  need(num, 1, 99, 'readFraction');
  need(den, 2, 99, 'readFraction');
  return readNumber(den) + 'ぶんの' + readNumber(num);
}

/** 講義列出的並列讀法（key 同 data/supplements/numbers.json）。第一讀法由函式產生。 */
export const NUMBER_ALTS = {
  0: ['れい'], 4: ['し'], 7: ['しち'], 9: ['く'],
  14: ['じゅうし'], 17: ['じゅうしち'], 19: ['じゅうく'], 70: ['しちじゅう'],
};

/** 講義同格列出的並列讀法（key 同 data/supplements/clock-date.json）。第一讀法由 readHour 等產生。 */
export const CLOCK_ALTS = {
  'minute:7': ['しちふん'],
  'minute:10': ['じっぷん'],
  'minute:30': ['さんじっぷん'],
};

/** 疑問詞與「半」。不規則連濁（なんぷん）與特例，明表。 */
export const CLOCK_Q = {
  hour: 'なんじ', minute: 'なんぷん', month: 'なんがつ', day: 'なんにち', half: 'はん',
};
