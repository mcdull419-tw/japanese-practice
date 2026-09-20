// 練習畫面。所有判斷邏輯（對錯、grade）一律交給 core/grading.js，
// 這裡只負責 DOM 渲染與事件綁定，不得自行比對字串或評分。
import { gradeAnswer } from '../core/grading.js';
import { makeEvent } from '../core/store.js';

const INPUT_ATTRS = 'lang="ja" autocorrect="off" autocapitalize="off" spellcheck="false" autocomplete="off"';

export function renderSession(host, deps) {
  const { items, store, deviceId, nextSeq, medianRt, onDone } = deps;
  let idx = 0, shownAt = 0, usedHint = false;

  function showItem() {
    if (idx >= items.length) return onDone();
    const it = items[idx];
    usedHint = false;
    host.innerHTML = `
      <div class="prompt">${escapeHtml(it.prompt.text)}</div>
      <div class="hint">${escapeHtml(it.prompt.hint || '')}</div>
      <input id="ans" type="text" ${INPUT_ATTRS}>
      <button id="submit">送出</button>
      <button id="hint">看提示</button>
      <div class="progress">${idx + 1} / ${items.length}</div>`;
    shownAt = Date.now();
    host.querySelector('#ans').focus();
    host.querySelector('#submit').onclick = submit;
    host.querySelector('#hint').onclick = () => { usedHint = true; revealHint(it); };
    host.querySelector('#ans').onkeydown = (e) => { if (e.key === 'Enter') submit(); };
  }

  async function submit() {
    const it = items[idx];
    const input = host.querySelector('#ans').value;
    const rt = Date.now() - shownAt;
    // 判定一律交給 core，ui 不得自行比對字串
    const { correct, grade } = gradeAnswer(input, it, rt, medianRt(it.engine), usedHint);
    await store.appendEvents([
      makeEvent(deviceId, nextSeq(), it.id, grade, rt, 'text', Math.floor(Date.now() / 1000)),
    ]);
    showResult(it, input, correct);
  }

  function showResult(it, input, correct) {
    host.innerHTML = `
      <div class="verdict">${correct ? '正確' : '再看一次'}</div>
      <div class="answer">正解：${escapeHtml(it.answer)}</div>
      <div class="source">出處：${escapeHtml(it.source_ref)}</div>
      ${correct ? '' : '<button id="also-ok">我這樣寫也對</button>'}
      <button id="next">下一題</button>`;
    host.querySelector('#next').onclick = () => { idx += 1; showItem(); };
    const alsoOk = host.querySelector('#also-ok');
    if (alsoOk) {
      alsoOk.onclick = () => {
        deps.acceptAlternative(it.id, input);
        host.querySelector('.verdict').textContent = '正確（已記錄你的寫法）';
        alsoOk.remove();
      };
    }
  }

  function revealHint(it) {
    host.querySelector('.hint').textContent = `${it.prompt.hint || ''}（開頭：${it.answer.slice(0, 1)}）`;
  }

  showItem();
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
