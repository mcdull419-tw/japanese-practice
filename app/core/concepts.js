/**
 * 概念層：把「知識點」抽象成 concept id，並將 SRS 熟悉度聚合成六類技能分數。
 *
 * 概念 id 格式（規格 §5.2）：
 *   w:<kana>          單字字義
 *   w:<kana>:reading  漢字讀音
 *   w:<kana>:group    該單字（動詞）的分類歸屬
 *   r:<form>:group<I|II|III>  變化規則本身
 *   p:*  助詞　g:*  句型　c:*／n:*  量詞數字
 */
import { conceptA } from './srs.js';

export const SKILLS = ['單字', '讀音', '變化', '助詞', '句型', '數量'];

export function skillOf(conceptId) {
  if (typeof conceptId !== 'string') return null;
  // 後綴必須先判斷：w:X:reading 與 w:X:group 都以 w: 開頭，
  // 若先比對前綴會把它們誤歸成「單字」。
  if (conceptId.endsWith(':reading')) return '讀音';
  if (conceptId.endsWith(':group')) return '變化';
  if (conceptId.startsWith('r:')) return '變化';
  if (conceptId.startsWith('w:')) return '單字';
  if (conceptId.startsWith('p:')) return '助詞';
  if (conceptId.startsWith('g:')) return '句型';
  if (conceptId.startsWith('c:') || conceptId.startsWith('n:')) return '數量';
  return null;
}

/**
 * 概念 id 一律以引用形（v.kanji || v.kana）為 lemma，與 verbs.json 的鍵、
 * Task 9 變換題生成器的 conceptsForConjugation 呼叫方式一致——
 * 否則同一個詞在 recall／transform 兩個引擎下會用不同名字命名概念，
 * 熟悉度分散在兩套命名下，儀表板與排程都會失準（比「兩個詞共用一個概念」更嚴重）。
 *
 * 這個粒度同時也修正了「同假名不同動詞」的問題（規格 §5.2 的 <kana> 若照字面
 * 理解為單純假名會讓 起きます／置きます 共用同一熟悉度）：
 *   起きます／置きます  → 引用形不同 → 分開的概念（正確：不同動詞）
 *   休みます（第4課/第11課，同詞不同語義）→ 引用形相同 → 共用概念（正確：同一個詞）
 */
export function conceptsForVocab(v) {
  const cite = v.kanji || v.kana;
  const ids = [`w:${cite}`];
  if (v.kanji) ids.push(`w:${cite}:reading`);
  return ids;
}

export function conceptsForConjugation(kana, group, form) {
  return [`r:${form}:group${group}`, `w:${kana}:group`];
}

/**
 * 形容詞的概念與動詞同構：變化規則本身，加上「這個詞屬於哪一類」。
 * 類別用 iadj／naadj 而非 I／II／III，才不會與動詞的 r:te:groupI 撞名——
 * 兩者都是「變化」技能底下的概念，命名空間必須分得開。
 */
export function conceptsForAdjective(citation, type, form) {
  return [`r:${form}:${type}adj`, `w:${citation}:group`];
}

/**
 * 規格 §7.6：技能熟悉度 = 該技能底下「複習範圍內」所有概念的 A 之算術平均。
 *
 * scopeConceptIds 是「範圍內存在哪些概念」的完整清單（含從未考過的），由呼叫端
 * 從目前候選題庫的 item.covers 蒐集而來——這是本函式與舊版最大的差異：舊版只
 * 走訪 conceptStates（也就是「至少練過一次」的概念），練 20 題就只在這 20 個
 * 概念上取平均，儀表板必然逼近滿分。現在改成走訪範圍內的全部概念，未考過的
 * 以 A=0 計入分母，數字才會從 0% 開始長，才反映真實進度（規格 §7.6 第 1 點）。
 *
 * 刻意不加 log(1+reps) 權重（規格 §7.6 第 2 點，不要「修好」這件事）：舊版加權
 * 是為了避免「只練過一次」的概念主導平均，但在「未考過也計入分母」的前提下，
 * 權重會讓 reps=0 的概念權重變成 0、被靜靜排除於平均之外，直接抵銷第 1 點，
 * 使用者又會看到剛練完就接近 100% 的老問題。純算術平均才是設計要求。
 *
 * 回傳 { scores, counts }：
 *   scores[skill] — 0~1 的平均分數；該技能在範圍內完全沒有概念時為 null
 *                   （這與「有概念但都是 0 分」不同，不能混為一談）。
 *   counts[skill] — { practiced, total }，供儀表板顯示「已練 N / 共 M」。
 */
export function aggregateSkills(conceptStates, scopeConceptIds) {
  const totals = Object.fromEntries(
    SKILLS.map((s) => [s, { sum: 0, total: 0, practiced: 0 }]));

  for (const id of new Set(scopeConceptIds)) {
    const skill = skillOf(id);
    if (!skill) continue;
    const st = conceptStates.get(id);
    totals[skill].sum += conceptA(conceptStates, id);
    totals[skill].total += 1;
    if (st && st.reps > 0) totals[skill].practiced += 1;
  }

  const scores = {};
  const counts = {};
  for (const s of SKILLS) {
    const t = totals[s];
    scores[s] = t.total > 0 ? t.sum / t.total : null;
    counts[s] = { practiced: t.practiced, total: t.total };
  }
  return { scores, counts };
}
