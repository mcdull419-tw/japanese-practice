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

export function conceptsForVocab(v) {
  const ids = [`w:${v.kana}`];
  if (v.kanji) ids.push(`w:${v.kana}:reading`);
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
