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

/** 規格 §7.6：權重取 log(1+複習次數)，避免只練過一次的概念左右大局。 */
export function aggregateSkills(conceptR) {
  const acc = Object.fromEntries(SKILLS.map((s) => [s, { sum: 0, w: 0 }]));
  for (const [id, st] of conceptR) {
    const skill = skillOf(id);
    if (!skill) continue;
    const w = Math.log(1 + (st.reps ?? 0));
    if (w <= 0) continue;
    acc[skill].sum += st.R * w;
    acc[skill].w += w;
  }
  return Object.fromEntries(
    SKILLS.map((s) => [s, acc[s].w > 0 ? acc[s].sum / acc[s].w : null]));
}
