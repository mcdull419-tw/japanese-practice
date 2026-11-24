/**
 * 漢字／假名寫法不拘的比對（整句題用）。
 *
 * 問題：練習Ａ／Ｂ 的答案是課本那一句的寫法（「わたしは毎朝6じに起きます」），
 * 原本只收那一種寫法。使用者打「わたしはまいあさ6じにおきます」或
 * 「私は毎朝6時に起きます」都被判錯——要猜中課本在哪裡寫漢字、哪裡寫假名。
 *
 * 做法：把答案切成詞，每個漢字詞記下它的讀音；比對時每個詞寫漢字或寫讀音都算，
 * 一句裡混著寫也行。讀音取自答案本身（詞典＋上下文規則），不靠猜使用者的漢字，
 * 因此「人」在「ドイツ人」裡是じん、在「会社の人」裡是ひと，各自判。
 *
 * 反方向（答案寫假名、使用者寫漢字：答案「かいません」、使用者「買いません」）
 * 則把使用者的漢字用詞典換成讀音再比一次。
 *
 * 數字一律照打阿拉伯數字；數字後的量詞（時／じ、分／ふん、回／かい…）兩種寫法都收。
 */
import { toHiragana, stripSpaces } from '../lang/kana.js';
import { stripQuotes } from './normalize.js';
import { okuriganaReading } from './ruby.js';

const KANJI = /[一-鿿々]/;
const KATAKANA = /[ァ-ヺー]/;
const DIGIT = /[0-9]/;

/**
 * 數字後的量詞：漢字寫法 → 可能的假名寫法。數字的音變（ぷん、がい、っか）不在這裡處理：
 * 數字本身照打阿拉伯數字，量詞的兩種常見唸法都收，寧可略寬也不要把對的判錯。
 */
const COUNTERS = [
  ['時間', ['じかん']], ['週間', ['しゅうかん']], ['か月', ['かげつ']], ['ヶ月', ['かげつ']],
  ['カ月', ['かげつ']], ['時', ['じ']], ['分', ['ふん', 'ぷん']], ['半', ['はん']],
  ['月', ['がつ']], ['日', ['にち', 'か']], ['年', ['ねん']], ['回', ['かい']],
  ['階', ['かい', 'がい']], ['枚', ['まい']], ['台', ['だい']], ['円', ['えん']],
  ['人', ['にん', 'り']], ['歳', ['さい']], ['才', ['さい']], ['番', ['ばん']],
  ['本', ['ほん', 'ぽん', 'ぼん']], ['冊', ['さつ']], ['匹', ['ひき', 'ぴき', 'びき']],
  ['個', ['こ']], ['杯', ['はい', 'ぱい', 'ばい']],
];
// 答案寫假名量詞（「4じ５ふん」）時反查：同一個假名可能對應多個漢字（かい＝回／階）。
const COUNTER_BY_KANA = new Map();
for (const [kanji, kanas] of COUNTERS) {
  for (const k of kanas) {
    if (!COUNTER_BY_KANA.has(k)) COUNTER_BY_KANA.set(k, new Set());
    COUNTER_BY_KANA.get(k).add(kanji);
  }
}
const COUNTER_KEYS = [...new Set([
  ...COUNTERS.map(([k]) => k), ...COUNTER_BY_KANA.keys(),
])].sort((a, b) => b.length - a.length);

/**
 * 詞典查不到、或詞典刻意不收的多讀音字（ruby-lexicon.json 的 ambiguous 區），
 * 依前後文決定讀音。只收練習Ａ／Ｂ 答案裡實際出現的情形；判不出來就回 null，
 * 該字只收漢字寫法（與修改前相同，不會更糟）。
 */
function contextReading(ch, prev, next) {
  const okuri = okuriganaReading(ch, next);
  if (okuri) return okuri;
  switch (ch) {
    case '人':
      if (prev && (KATAKANA.test(prev) || KANJI.test(prev))) return 'じん'; // ドイツ人、日本人
      return 'ひと'; // あの人、会社の人、どんな人
    case '何':
      return /^[をもがにかとや]/.test(next || '') ? 'なに' : 'なん'; // 何を／何も；何時、何年
    case '月':
      return prev === 'か' || prev === 'ヶ' || prev === 'カ' ? 'げつ' : null;
    case '少':
      return next === 'し' ? 'すこ' : next === 'な' ? 'すく' : null;
    case '父':
      return prev === 'お' ? 'とう' : 'ちち';
    case '母':
      return prev === 'お' ? 'かあ' : 'はは';
    case '生':
      return next === 'け' ? 'い' : null; // 生け花
    case '半':
      return 'はん'; // 10時半
    case '上':
      return next === 'が' ? 'あ' : 'うえ';
    default:
      return null;
  }
}

/** 全形英數轉半形、去空白、去引號、數字裡的千分位逗號去掉（1,500 與 1500 都算）。 */
function prep(s) {
  return stripQuotes(stripSpaces(String(s).replace(/[！-～]/g,
    (c) => String.fromCharCode(c.charCodeAt(0) - 0xfee0))))
    .replace(/(\d),(?=\d)/g, '$1')
    .replace(/[。.．]+$/u, '');
}

/**
 * 把一句切成 token，每個 token 是「可接受的寫法」清單（已轉平假名）。
 * 純文字 token 只有一種寫法。
 */
export function readingTokens(text, lex) {
  const s = prep(text);
  const out = [];
  let i = 0;
  while (i < s.length) {
    const ch = s[i];
    if (DIGIT.test(ch)) {
      let j = i;
      while (j < s.length && DIGIT.test(s[j])) j++;
      out.push([s.slice(i, j)]);
      i = j;
      const rest = s.slice(i);
      const key = COUNTER_KEYS.find((k) => rest.startsWith(k));
      if (key) {
        const forms = new Set([key]);
        for (const [kanji, kanas] of COUNTERS) {
          if (kanji === key) kanas.forEach((k) => forms.add(k));
        }
        for (const kanji of COUNTER_BY_KANA.get(key) || []) forms.add(kanji);
        out.push([...forms].map(toHiragana));
        i += key.length;
      }
      continue;
    }
    if (KANJI.test(ch)) {
      let hit = null;
      if (lex) {
        let j = i;
        while (j < s.length && KANJI.test(s[j])) j++;
        for (let len = j - i; len > 0; len--) {
          if (lex.has(s.slice(i, i + len))) { hit = s.slice(i, i + len); break; }
        }
      }
      if (hit) {
        out.push([hit, toHiragana(lex.get(hit))]);
        i += hit.length;
      } else {
        const r = contextReading(ch, s[i - 1], s[i + 1]);
        out.push(r ? [ch, r] : [ch]);
        i += 1;
      }
      continue;
    }
    out.push([toHiragana(ch)]);
    i += 1;
  }
  return out;
}

/** 使用者打的漢字換成讀音（給「答案寫假名、使用者寫漢字」的方向用）。 */
function inputToKana(input, lex) {
  return readingTokens(input, lex).map((forms) => forms[forms.length - 1]).join('');
}

/**
 * 輸入端用的詞典：振假名詞典再加上課本單字表推得的「漢字段 → 讀音」。
 *
 * 振假名詞典只收練習Ａ／Ｂ 題目裡出現過的漢字；答案寫假名（「わたしは何もかいません」）
 * 而使用者寫漢字（「私は何も買いません」）時，私、買 不在其中。單字表有
 * 「私／わたし」「買います／かいます」，去掉共同的假名頭尾即得 私→わたし、買→か。
 *
 * 只用在輸入端，不拿來切答案：答案的讀音已逐句看過，不受這裡影響。
 * 一個漢字段推出兩種讀音、或屬於多讀音字者不收——收了會把對的判錯。
 */
export function buildInputLexicon(vocab, lex, ambiguous = []) {
  const seen = new Map();
  const skip = new Set(ambiguous);
  for (const v of vocab || []) {
    if (!v.kanji || !v.kana) continue;
    const kana = v.kana.split(/[／/]/)[0].trim();
    for (const form of v.kanji.split(/[、，,／/]/).map((x) => x.trim()).filter(Boolean)) {
      let a = form, b = kana;
      while (a && b && a[a.length - 1] === b[b.length - 1] && !KANJI.test(a[a.length - 1])) {
        a = a.slice(0, -1); b = b.slice(0, -1);
      }
      while (a && b && a[0] === b[0] && !KANJI.test(a[0])) { a = a.slice(1); b = b.slice(1); }
      if (!a || !b || ![...a].every((c) => KANJI.test(c)) || skip.has(a)) continue;
      if (!/^[\u3041-\u309f\u30a1-\u30fc]+$/.test(b)) continue;
      if (!seen.has(a)) seen.set(a, new Set());
      seen.get(a).add(b);
    }
  }
  const out = new Map();
  for (const [base, readings] of seen) if (readings.size === 1) out.set(base, [...readings][0]);
  for (const [base, kana] of lex || []) out.set(base, kana);
  return out;
}

function matchTokens(s, tokens) {
  const memo = new Map();
  const go = (i, k) => {
    if (k === tokens.length) return i === s.length;
    const key = i * 1000 + k;
    if (memo.has(key)) return memo.get(key);
    let ok = false;
    for (const f of tokens[k]) {
      if (f && s.startsWith(f, i) && go(i + f.length, k + 1)) { ok = true; break; }
    }
    memo.set(key, ok);
    return ok;
  };
  return go(0, 0);
}

/** 輸入是否與 target 同一句話（每個漢字詞寫漢字或讀音皆可，可混寫）。 */
export function matchesReading(input, target, lex, inputLex = lex) {
  // 答案也用合併詞典切：振假名詞典只收課本句子標過讀音的詞，練習Ｂ 答案裡的
  // 練習、残業、目、歯 不在其中；只靠它會把「練習」切成 練＋習(なら)。
  // 合併詞典裡振假名詞典優先，單字表只補缺。
  const tokens = readingTokens(target, inputLex || lex);
  const raw = toHiragana(prep(input));
  if (raw.length === 0) return false;
  if (matchTokens(raw, tokens)) return true;
  return matchTokens(toHiragana(inputToKana(input, inputLex)), tokens);
}
