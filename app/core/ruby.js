/**
 * 振假名切詞（規格 §9.3、§13 決定 9）。純函式，回傳 token 陣列，不產生 DOM——
 * `<ruby>` 由 ui/html.js 組裝，core 不得碰 document。
 *
 * 兩條路徑共用同一個 token 形狀：
 *   - annotateWithMarks：課本 sentences[].ruby 的精確標註，優先使用
 *   - annotateWithLexicon：練習Ａ／Ｂ 沒有標註，以詞典最長匹配
 */

/**
 * 標註位置對不上時「跳過該筆」而不是拋錯：ruby 是輔助資訊，語料重抽而位移
 * 不該讓整個題目渲染失敗。真正的把關在 tests/app/test_ruby_lexicon.js 的
 * 漂移測試——那裡對不上就紅燈。
 */
export function annotateWithMarks(text, marks) {
  if (typeof text !== 'string' || text.length === 0) return [];
  const valid = (marks || [])
    .filter((m) => m && typeof m.at === 'number' && typeof m.base === 'string'
      && text.slice(m.at, m.at + m.base.length) === m.base)
    .sort((a, b) => a.at - b.at);

  const out = [];
  let cursor = 0;
  for (const m of valid) {
    if (m.at < cursor) continue; // 重疊標註：保留先出現者
    if (m.at > cursor) out.push({ t: 'text', s: text.slice(cursor, m.at) });
    out.push({ t: 'ruby', base: m.base, kana: m.kana });
    cursor = m.at + m.base.length;
  }
  if (cursor < text.length) out.push({ t: 'text', s: text.slice(cursor) });
  return out;
}

const KANJI_RUN = /[\u4e00-\u9fff]+/g;

/**
 * manual 覆蓋 auto：auto 區是從語料機械產生的，重跑會被整區覆寫；人工補的
 * 判讀必須活得比重跑久，因此分成兩區而不是混在同一個物件裡。
 */
export function buildLexicon(json) {
  const lex = new Map();
  for (const [base, kana] of Object.entries((json && json.auto) || {})) lex.set(base, kana);
  for (const [base, kana] of Object.entries((json && json.manual) || {})) lex.set(base, kana);
  return lex;
}

/**
 * 讀音由後面的送假名決定的多讀音字（ruby-lexicon.json 的 ambiguous 區）：
 * 来ます／来た／来て＝き、来る＝く、来ない＝こ；入れる＝い、入る＝はい；
 * 出す＝だ、出る／出かける＝で；熱い＝あつ、熱（發燒）＝ねつ。
 * 只看緊接在後的一個假名，判不出來回 null（照舊不加注，不猜）。
 */
const OKURIGANA = {
  来: [[/^[まただてよ]/, 'き'], [/^[るれ]/, 'く'], [/^[なこい]/, 'こ']],
  入: [[/^れ/, 'い'], [/^[りっらる]/, 'はい']],
  出: [[/^[しさすそせ]/, 'だ'], [/^[まてかたるなよらろ]/, 'で']],
  熱: [[/^[いくかさ]/, 'あつ'], [/^$|^[^ぁ-ん]|^[がをはもで]/, 'ねつ']],
};

export function okuriganaReading(ch, next) {
  for (const [re, kana] of OKURIGANA[ch] || []) if (re.test(next || '')) return kana;
  return null;
}

/** 相鄰 text token 合併，讓輸出與「沒加注」時完全一致，測試才好寫也好讀。 */
function pushText(out, s) {
  if (!s) return;
  const last = out[out.length - 1];
  if (last && last.t === 'text') last.s += s;
  else out.push({ t: 'text', s });
}

/**
 * 只在漢字連續段上做最長匹配。匹配不到就退一個字元繼續試，因此
 * 「手紙」在詞典只有「紙」時會切成 text('手') ＋ ruby('紙')，而不是整段放棄。
 */
export function annotateWithLexicon(text, lex) {
  if (typeof text !== 'string' || text.length === 0) return [];
  const out = [];
  let cursor = 0;
  for (const m of text.matchAll(KANJI_RUN)) {
    pushText(out, text.slice(cursor, m.index));
    const run = m[0];
    let i = 0;
    while (i < run.length) {
      let hit = null;
      for (let len = run.length - i; len > 0; len--) {
        const cand = run.slice(i, i + len);
        if (lex.has(cand)) { hit = cand; break; }
      }
      const okuri = !hit && i === run.length - 1
        ? okuriganaReading(run[i], text[m.index + run.length]) : null;
      if (hit) {
        out.push({ t: 'ruby', base: hit, kana: lex.get(hit) });
        i += hit.length;
      } else if (okuri) {
        out.push({ t: 'ruby', base: run[i], kana: okuri });
        i += 1;
      } else {
        pushText(out, run[i]);
        i += 1;
      }
    }
    cursor = m.index + run.length;
  }
  pushText(out, text.slice(cursor));
  return out;
}
