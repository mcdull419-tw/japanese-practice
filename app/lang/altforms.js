/**
 * 課本部分詞條在同一欄位裡用分隔符列出多個寫法（例：漢字欄「作ります、造ります」、
 * 「暑い、熱い」），分隔符可能是 、，／,/ 這幾種（規格外觀察，修正 B／C）。
 * 這裡統一拆開，供 recall.js（每個寫法都要能被判對）與 transform.js
 * （取第一個寫法作引用形查 verbsTable、其餘寫法的變化也算 alternatives）共用，
 * 避免兩處各自維護一份分隔符正規式而漂移。
 */
const DELIMS = /[、，,／/]/;

export function splitForms(s) {
  if (typeof s !== 'string' || s.length === 0) return [];
  return s.split(DELIMS).map((x) => x.trim()).filter(Boolean);
}

/**
 * 修正（假名欄多種寫法）：假名欄也會用分隔符列出多個說法（例：
 * おっと／しゅじん、IMC／パワーでんき／ブラジルエアー），比照漢字欄，
 * 每個寫法都該各自算對。
 *
 * 但假名欄的「、」不能比照漢字欄一併當分隔符：漢字欄的「、」只出現在
 * 「作ります、造ります」這類並列寫法裡；假名欄的「、」還會出現在句子
 * 本身的標點裡（例：「いいえ、けっこうです。」「じゃ、また。」），拆開
 * 會產生斷句垃圾，不是多種說法。全語料查證：假名欄從未用「，」「,」
 * 當並列分隔符，只用全形／半形斜線；因此這裡只切「／」「/」，
 * 刻意不含 DELIMS 裡的「、，,」，把句子標點排除在外。
 */
const KANA_DELIMS = /[／/]/;

export function splitKanaForms(s) {
  if (typeof s !== 'string' || s.length === 0) return [];
  return s.split(KANA_DELIMS).map((x) => x.trim()).filter(Boolean);
}
