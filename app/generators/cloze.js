/**
 * 挖空題（需求 #5 助詞填空）。
 *
 * 素材是 data/particles.json 的人工標註，不是規則猜測——規則找得到助詞在哪，
 * 但分不出「に 表對象」與「に 表時間」是兩個不同的知識點（規格 §5.2）。
 * 沒有標註的句子一律不產題：寧可少出題，也不要把錯的歸因寫進 SRS。
 *
 * 單一考點題，covers 只有一個概念，答錯的歸因明確（規格 §7.5 第1點）。
 */
import { skillOf } from '../core/concepts.js';

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

export function* generate(sentences, particleMarks) {
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
}
