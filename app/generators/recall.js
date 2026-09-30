import { conceptsForVocab, skillOf } from '../core/concepts.js';
import { splitForms, splitKanaForms } from '../lang/altforms.js';

export const ENGINE = 'recall';

function makeItem({ id, v, promptText, hint, answer, alternatives, covers }) {
  return {
    id, engine: ENGINE, lesson: v.lesson, requires_lesson: v.lesson,
    covers, skills: [...new Set(covers.map(skillOf).filter(Boolean))],
    prompt: { type: 'text', text: promptText, hint },
    answer, alternatives,
    source_ref: `第${v.lesson}課 ことば${v.no ? ` ${v.no}` : ''}`,
  };
}

/**
 * 全語料共 749 筆單字中，有 11 個假名被兩筆以上不同的 vocab 條目共用——
 * 有的是真同形異義動詞（例：おきます＝起きます／置きます，とります＝撮ります／取ります，
 * 與 Task 3/4 在 verbs.json 發現的 おきます 衝突同一來源），
 * 有的是同一個詞在後面課次以不同語義／用法重新出現（例：どちら、あります、それから）。
 * 兩種情況都會讓 `recall:<kana>:<variant>` 撞出重複 id，導致後出現的項目
 * 在以 id 為鍵的題庫中悄悄覆蓋先出現的項目，且不會有任何錯誤訊息。
 *
 * 消歧只在真的撞名時才加後綴，藉此讓不撞名的絕大多數單字維持原本乾淨的 id 格式。
 * 後綴取自課本既定的「課次－編號」（v.lesson / v.no），兩者皆為資料內容而非陣列位置或亂數，
 * 對同一份語料重新生成必得到相同結果。
 */
function disambiguator(v) {
  return v.no != null ? `L${v.lesson}-${v.no}` : `L${v.lesson}`;
}

const CHOICE_COUNT = 4;

/**
 * FNV-1a：把 item id 攤成一個整數種子。用途只有一個——讓誘答的挑選與排序
 * 是 id 的函式，而不是呼叫時機的函式。
 *
 * 規格 §5.3 要求 id 決定性，但只有 id 決定性是不夠的：選項若每次不同，
 * 同一個 id 在 SRS 裡記到的就不是同一道題，歷史照樣失效。
 */
function seedOf(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h;
}

/**
 * 選項用的中文釋義：截到第一個全形括號之前。
 *
 * 課本的中文欄常夾著用法說明（「他，她，那個人 （ あの かた ）（“あのかた”是
 * “あのひと”的禮貌形）」）。整串當選項有兩個問題：按鈕長到爆版，更糟的是
 * 長度本身變成線索——四個選項裡只有一個特別長，不必看懂也猜得到。
 *
 * 整筆都是說明者（「（用於小孩的名字後）」）截完會是空字串，退回原字串：
 * 那類詞的釋義本來就只有說明，沒有更短的寫法。
 */
function shortZh(zh) {
  const cut = String(zh).split('（')[0].trim();
  return cut || String(zh).trim();
}

/** 以種子決定性地取 n 個不重複元素（洗牌後取前 n 個）。 */
function pickDeterministic(pool, n, seed) {
  const arr = [...pool];
  let s = seed;
  for (let i = arr.length - 1; i > 0; i--) {
    s = (Math.imul(s, 1103515245) + 12345) >>> 0;
    const j = s % (i + 1);
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr.slice(0, n);
}

export function* generate(vocabList) {
  const usable = vocabList.filter((v) => v.kana && v.zh);
  const byKana = new Map();
  for (const v of usable) {
    if (!byKana.has(v.kana)) byKana.set(v.kana, []);
    byKana.get(v.kana).push(v);
  }

  // 誘答池：同一課的其他中文釋義。跨課取詞會讓使用者靠「這課沒教過」猜答案。
  const zhByLesson = new Map();
  for (const v of usable) {
    if (!zhByLesson.has(v.lesson)) zhByLesson.set(v.lesson, new Set());
    zhByLesson.get(v.lesson).add(shortZh(v.zh));
  }

  for (const v of usable) {
    const collides = byKana.get(v.kana).length > 1;
    const key = collides ? `${v.kana}:${disambiguator(v)}` : v.kana;
    // covers 一律取自 conceptsForVocab，才能與引用形 lemma 命名保持一致
    // （item id 仍以假名為鍵，兩個命名空間互不相依，見 disambiguator 注解）。
    const [meaningConcept, readingConcept] = conceptsForVocab(v);

    // 修正 B：課本有些詞的漢字欄用分隔符列出多個寫法（例：作ります、造ります）。
    // 若整串當成唯一一個 alternative，使用者只打其中一個寫法會被判錯。
    // 這裡把每個寫法都拆成獨立的 alternative，原始整串也保留（不影響原本行為）。
    //
    // 修正（假名欄多種寫法）：假名欄也有同樣的情形（おっと／しゅじん），
    // 用 splitKanaForms 拆（只切「／」「/」，見 altforms.js 註解，
    // 不會誤傷句子標點「、」）。沒有分隔符時回傳單一元素，即原字串本身，
    // 併入 Set 後不產生多餘項目。
    const zh2jpAlts = [...new Set([
      ...(v.kanji ? [v.kanji, ...splitForms(v.kanji)] : []),
      ...splitKanaForms(v.kana),
    ])];
    yield makeItem({
      id: `recall:${key}:zh2jp`, v,
      promptText: v.zh, hint: '寫出日文',
      answer: v.kana,
      alternatives: zh2jpAlts,
      covers: [meaningConcept],
    });
    if (v.kanji) {
      yield makeItem({
        id: `recall:${key}:kanji2kana`, v,
        promptText: v.kanji, hint: '寫出讀音（平假名）',
        answer: v.kana, alternatives: [],
        covers: [readingConcept],
      });
    }

    // 需求 #1 的日→中方向。打字輸入中文對自學者沒有練習價值（看得懂日文的人
    // 打得出中文），改為四選一——分辨近義詞才是這個方向真正要練的能力。
    const correct = shortZh(v.zh);
    // 截短後可能與同課別的詞撞在一起（兩個詞的主釋義相同），撞到就不能當誘答
    // ——四個選項裡有兩個對的，使用者選了另一個會被判錯。
    const pool = [...(zhByLesson.get(v.lesson) || [])].filter((z) => z !== correct).sort();
    if (pool.length >= CHOICE_COUNT - 1) {
      const id = `recall:${key}:jp2zh`;
      const seed = seedOf(id);
      const distractors = pickDeterministic(pool, CHOICE_COUNT - 1, seed);
      const choices = pickDeterministic([correct, ...distractors], CHOICE_COUNT, seed ^ 0x5bf03635);
      yield {
        ...makeItem({
          id, v,
          promptText: v.kanji || v.kana, hint: '選出中文意思',
          answer: correct, alternatives: [],
          covers: [meaningConcept],
        }),
        choices,
      };
    }
  }
}
