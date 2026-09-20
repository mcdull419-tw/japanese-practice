/**
 * 載入 Phase 0 產出的課次 JSON 並建立索引。
 * loader 以注入方式提供，讓瀏覽器（fetch）與 Node 測試（fs）共用同一份邏輯。
 */
export async function loadLessons(lessonNumbers, loader) {
  const out = new Map();
  for (const n of lessonNumbers) {
    out.set(n, await loader(n));
  }
  return out;
}

export function buildIndex(lessonsMap) {
  const vocab = [];
  const sentences = [];
  for (const [n, data] of [...lessonsMap.entries()].sort((a, b) => a[0] - b[0])) {
    for (const v of data.vocab || []) vocab.push({ ...v, lesson: n });
    for (const s of data.sentences || []) sentences.push({ ...s, lesson: n });
  }
  return { vocab, sentences };
}
