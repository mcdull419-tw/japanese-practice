export const FORMS = ['masu', 'masen', 'mashita', 'masendeshita', 'te'];

/** 各形態在課本中首次出現的課次，用於範圍過濾（規格 §5.3 requires_lesson）。 */
export const FORM_LESSON = { masu: 4, masen: 4, mashita: 4, masendeshita: 4, te: 14 };

const TENSE_SUFFIX = {
  masu: 'ます', masen: 'ません', mashita: 'ました', masendeshita: 'ませんでした',
};

/** I 類：ます形語幹末音 → て形語尾。 */
const I_TE = new Map([
  ['い', 'って'], ['ち', 'って'], ['り', 'って'],
  ['に', 'んで'], ['び', 'んで'], ['み', 'んで'],
  ['き', 'いて'], ['ぎ', 'いで'], ['し', 'して'],
]);

/**
 * 唯一的 I 類て形不規則（規格 §6.4）：行きます。
 * 同時收錄假名鍵與引用形（漢字）鍵——動詞變化題現在以漢字出題（修正 D），
 * conjugate() 會直接收到「行きます」而非「いきます」，若只收假名鍵，
 * 漢字形會落到一般規則（き→いて），算出「行いて」這種錯誤變化。
 * 不存成固定字串而是在下方比對後用 stem 現算，兩種鍵才都能保留各自的字面（漢字／假名）。
 */
const I_TE_IRREGULAR = new Set(['いきます', '行きます']);

export function conjugate(masuForm, group, form) {
  if (typeof masuForm !== 'string' || !masuForm.endsWith('ます')) {
    throw new Error(`conjugate: 需要ます形，收到 ${JSON.stringify(masuForm)}`);
  }
  if (!['I', 'II', 'III'].includes(group)) {
    throw new Error(`conjugate: 未知的 group ${JSON.stringify(group)}`);
  }
  if (!FORMS.includes(form)) {
    throw new Error(`conjugate: 未知的 form ${JSON.stringify(form)}`);
  }

  const stem = masuForm.slice(0, -2);
  if (form !== 'te') return stem + TENSE_SUFFIX[form];

  if (I_TE_IRREGULAR.has(masuForm)) return stem.slice(0, -1) + 'って';
  if (group === 'II') return stem + 'て';
  if (group === 'III') {
    // III 類 stem 一律以「し」或「き」結尾（します／きます），直接加て即可。
    // （不可用 stem + 'して'.slice(1) 這種寫法混淆視聽——雖然數值上等於
    // stem + 'て'，但容易誤讀誤改，改直接寫法。）
    return stem + 'て';
  }

  const last = stem.slice(-1);
  const ending = I_TE.get(last);
  if (!ending) throw new Error(`conjugate: I 類語幹末音 ${last} 無對應て形（${masuForm}）`);
  return stem.slice(0, -1) + ending;
}
