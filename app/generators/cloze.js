/**
 * 挖空題（需求 #5 助詞填空）。
 *
 * 素材是 data/particles.json 的人工標註，不是規則猜測——規則找得到助詞在哪，
 * 但分不出「に 表對象」與「に 表時間」是兩個不同的知識點（規格 §5.2）。
 * 沒有標註的句子一律不產題：寧可少出題，也不要把錯的歸因寫進 SRS。
 *
 * 單一考點題，covers 只有一個概念，答錯的歸因明確（規格 §7.5 第1點）。
 */
import { skillOf, conceptsForVocab } from '../core/concepts.js';
import { splitForms, splitKanaForms } from '../lang/altforms.js';

export const ENGINE = 'cloze';

const BLANK = '＿';

/**
 * 規格 §9.2 第二類：助詞的合法替代，生成時依規則列舉。
 * 只收課本範圍內確實兩者皆可的配對——過度列舉會讓真正的錯誤也被判對。
 */
const EQUIVALENT = {
  'p:e:direction': ['に'],       // 日本へ 行きます／日本に 行きます
  'p:ni:destination': ['へ'],
  'p:ni:source': ['から'],       // 山田さんに もらいました／山田さんから もらいました（第7課 文法4）
};

export function* generate(sentences, particleMarks, vocabList) {
  const byId = new Map(sentences.map((s) => [s.id, s]));

  for (const [sid, list] of Object.entries(particleMarks || {})) {
    const s = byId.get(sid);
    if (!s) continue; // 標註指向已不存在的句子（課次範圍未載入或語料變動），略過

    for (const m of list) {
      // 位置對不上就不出題。測試會在 CI 抓到這種漂移，這裡是執行期的第二道防線：
      // 錯位的題目會把答案挖在別的字上，比不出題有害得多。
      if (s.jp.slice(m.at, m.at + m.p.length) !== m.p) continue;

      const prompt = s.jp.slice(0, m.at) + BLANK + s.jp.slice(m.at + m.p.length);
      const alternatives = new Set([
        ...(s.alt || []),
        ...(EQUIVALENT[m.c] || []),
      ]);
      alternatives.delete(m.p); // 主答案不重複列進 alternatives

      const covers = [m.c];
      yield {
        id: `cloze:${sid}:${m.at}`,
        engine: ENGINE,
        lesson: s.lesson,
        // 助詞用法的解鎖課次就是它所在句子的課次——課本在哪一課用這個句型，
        // 該用法就是那一課教的。
        requires_lesson: s.lesson,
        covers,
        skills: [...new Set(covers.map(skillOf).filter(Boolean))],
        prompt: { type: 'text', text: prompt, hint: '填入助詞' },
        answer: m.p,
        alternatives: [...alternatives],
        source_ref: `第${s.lesson}課 ${s.section}-${s.no}`,
      };
    }
  }

  if (vocabList) yield* generatePhrases(sentences, vocabList);
}
/**
 * 與 particles.json 同一個素材範圍：会話 有說話者標籤（「山 田：」）、
 * 問題 是含題號與括號答案的多行混合體，都不是乾淨單句。
 */
const PHRASE_SECTIONS = new Set(['文型', '例文']);

/**
 * 內容詞之後只允許接助詞（或什麼都不接）。不設這道檢查，由長到短的比對
 * 會把「山田」切成「山」、把「何時」切成「何」——挖出來的答案是別的詞的一部分。
 */
const PHRASE_TAIL = new Set(['', 'は', 'が', 'を', 'に', 'で', 'と', 'へ', 'も', 'や', 'の',
  'から', 'まで', 'より', 'には', 'では', 'とは', 'へは', 'にも', 'でも', 'とも', 'へも',
  'からも', 'までも', 'か', 'ね', 'よ']);

/**
 * 詞組挖空（需求 #12）。挖掉整個詞組的內容詞，保留其後的助詞——
 * 助詞留著，題目才問得出「這裡該填哪個詞」而不是「這裡該填什麼都行」。
 *
 * 只在內容詞對得上 vocab 條目時才出題。對不上就沒有明確的 w: 概念可掛，
 * 答對答錯都無處歸因，那種題目對 SRS 沒有價值（規格 §7.5）。
 */
function* generatePhrases(sentences, vocabList) {
  // 引用形與假名兩種寫法都建索引：課本句子裡可能寫漢字也可能寫假名。
  const byForm = new Map();
  for (const v of vocabList) {
    if (!v.zh) continue;
    for (const form of [...(v.kanji ? splitForms(v.kanji) : []), ...splitKanaForms(v.kana || '')]) {
      if (form && !byForm.has(form)) byForm.set(form, v);
    }
  }

  for (const s of sentences) {
    if (!PHRASE_SECTIONS.has(s.section)) continue;
    let pos = 0;
    for (const chunk of s.jp.split(/([　 ]+)/)) {
      if (!chunk.trim()) { pos += chunk.length; continue; }
      const body = chunk.replace(/[。？！]+$/u, '');
      // 由長到短試切點：詞組可能是「手紙を」「手紙」或「手紙が」，
      // 取最長的成功比對，避免把「手」當成內容詞。
      for (let cut = body.length; cut >= 1; cut--) {
        const head = body.slice(0, cut);
        const v = byForm.get(head);
        if (!v || !PHRASE_TAIL.has(body.slice(cut))) continue;
        const covers = [conceptsForVocab(v)[0]];
        yield {
          id: `cloze:${s.id}:${pos}:phrase`,
          engine: ENGINE,
          lesson: s.lesson,
          requires_lesson: Math.max(s.lesson, v.lesson),
          covers,
          skills: [...new Set(covers.map(skillOf).filter(Boolean))],
          prompt: {
            type: 'text',
            text: s.jp.slice(0, pos) + BLANK + s.jp.slice(pos + cut),
            hint: v.zh,
          },
          answer: head,
          alternatives: [...new Set([
            ...(v.kanji ? splitForms(v.kanji) : []),
            ...splitKanaForms(v.kana || ''),
          ])].filter((x) => x !== head),
          source_ref: `第${s.lesson}課 ${s.section}-${s.no}`,
        };
        break; // 一個詞組只出一題
      }
      pos += chunk.length;
    }
  }
}
