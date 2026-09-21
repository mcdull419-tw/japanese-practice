import { conceptsForVocab, skillOf } from '../core/concepts.js';
import { splitForms } from '../lang/altforms.js';

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

export function* generate(vocabList) {
  const usable = vocabList.filter((v) => v.kana && v.zh);
  const byKana = new Map();
  for (const v of usable) {
    if (!byKana.has(v.kana)) byKana.set(v.kana, []);
    byKana.get(v.kana).push(v);
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
    const zh2jpAlts = v.kanji ? [...new Set([v.kanji, ...splitForms(v.kanji)])] : [];
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
  }
}
