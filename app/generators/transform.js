import { conjugate, FORM_LESSON } from '../lang/conjugation.js';
import { conceptsForConjugation, skillOf } from '../core/concepts.js';

export const ENGINE = 'transform';

const TARGETS = [
  { form: 'te', hint: 'て形' },
  { form: 'masen', hint: '否定形（ません）' },
  { form: 'mashita', hint: '過去形（ました）' },
  { form: 'masendeshita', hint: '過去否定形（ませんでした）' },
];

/**
 * 查表與 item id 一律用引用形（v.kanji || v.kana），不是假名。
 *
 * 全語料中 おきます 同時對應 起きます（II類，第4課）與 置きます（I類，第15課）。
 * 若用假名查表，其中一筆會覆蓋另一筆，讓第4課的基礎動詞算出錯誤的分類與て形
 * （置きます 的規則套到 起きます 上，答案會變成おいて而非おきて，那是教錯）。
 * 若用假名當 item id，兩者會產生相同的 id，SRS 會把兩個不同動詞的練習紀錄
 * 混在一起。引用形在全語料 71 個鍵中彼此不同，兩個問題都不存在。
 *
 * 每個引用形只產生一次變化題，即使同一個動詞在後面課次以不同語義／用法
 * 重新出現於單字表也一樣（例：休みます 第4課「休息」／第11課「請假」，
 * います 第10、11課各以不同例句重現）。變化規則不因語義而變，
 * 用第一次出現（課次最早）的那筆決定 lesson／source_ref 即可；
 * 若不去重，同一引用形會產生重複的 id，在以 id 為鍵的題庫中悄悄互相覆蓋
 * ——這是全語料驗證才會暴露的問題，三筆假資料測不出來。
 */
export function* generate(vocabList, verbsTable) {
  const seen = new Set();
  for (const v of vocabList) {
    const cite = v.kanji || v.kana;
    if (seen.has(cite)) continue;
    const info = verbsTable[cite];
    if (!info) continue; // 未收錄的動詞不猜分類，直接跳過
    seen.add(cite);

    for (const { form, hint } of TARGETS) {
      let answer;
      try {
        answer = conjugate(info.kana, info.group, form);
      } catch {
        continue; // 無法變化者略過，不產生錯誤題目
      }

      const covers = conceptsForConjugation(cite, info.group, form);
      yield {
        id: `conj:${cite}:masu2${form}`,
        engine: ENGINE,
        lesson: v.lesson,
        // 規格 §5.3：requires_lesson 取單字課次與目標形態解鎖課次的較大值。
        // 送ります 是第7課單字，但て形第14課才教，該題 requires_lesson 為14。
        requires_lesson: Math.max(v.lesson, FORM_LESSON[form]),
        covers,
        skills: [...new Set(covers.map(skillOf).filter(Boolean))],
        prompt: { type: 'text', text: info.kana, hint },
        answer,
        alternatives: [],
        source_ref: `第${v.lesson}課 ことば${v.no ? ` ${v.no}` : ''}`,
      };
    }
  }
}
