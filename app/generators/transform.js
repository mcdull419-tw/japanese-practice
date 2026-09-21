import { conjugate, FORM_LESSON } from '../lang/conjugation.js';
import { conceptsForConjugation, skillOf } from '../core/concepts.js';
import { splitForms } from '../lang/altforms.js';

export const ENGINE = 'transform';

// 修正 E：hint 括號裡的語尾等於直接洩漏答案（考「過去形」卻標「（ました）」，
// 使用者幾乎不用想）。只留形態名稱。
const TARGETS = [
  { form: 'te', hint: 'て形' },
  { form: 'masen', hint: '否定形' },
  { form: 'mashita', hint: '過去形' },
  { form: 'masendeshita', hint: '過去否定形' },
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
    // 修正 C：課本漢字欄偶爾用分隔符列出多個寫法（例：作ります、造ります），
    // 那不是單一引用形。取第一個寫法查 verbsTable／當 id，其餘寫法留著
    // 給下面算 alternatives（splitForms 對沒有分隔符的一般漢字形是不動點，
    // 一般動詞的行為完全不變）。
    const forms = v.kanji ? splitForms(v.kanji) : [];
    const cite = forms[0] || v.kana;
    if (seen.has(cite)) continue;
    const info = verbsTable[cite];
    if (!info) continue; // 未收錄的動詞不猜分類，直接跳過
    seen.add(cite);

    // 修正 D：動詞變化題以漢字出題（cite 就是引用形：漢字優先，沒有漢字才用假名，
    // 與 verbs.json 的鍵一致）。答案也用漢字形算，假名形（以及課本另列的其他
    // 漢字寫法）都收進 alternatives，使用者打漢字或打假名都要算對。
    const altCites = forms.slice(1);

    for (const { form, hint } of TARGETS) {
      let kanaAnswer, answer;
      try {
        kanaAnswer = conjugate(info.kana, info.group, form);
        answer = cite === info.kana ? kanaAnswer : conjugate(cite, info.group, form);
      } catch {
        continue; // 無法變化者略過，不產生錯誤題目
      }

      const alternatives = new Set();
      if (answer !== kanaAnswer) alternatives.add(kanaAnswer);
      for (const alt of altCites) {
        try {
          const altAnswer = conjugate(alt, info.group, form);
          if (altAnswer !== answer) alternatives.add(altAnswer);
        } catch {
          // 課本另一個寫法若剛好不合乎既有的て形規則（不應發生，但求穩健），
          // 忽略即可，不影響主答案。
        }
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
        prompt: { type: 'text', text: cite, hint },
        answer,
        alternatives: [...alternatives],
        source_ref: `第${v.lesson}課 ことば${v.no ? ` ${v.no}` : ''}`,
      };
    }
  }
}
