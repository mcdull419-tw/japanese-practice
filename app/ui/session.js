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
      <div class="progress">${idx + 1} / ${items.length}</div>
      <div class="recap-prompt">題目：${escapeHtml(it.prompt.text)}</div>
      <div class="recap-input">你的答案：${input ? escapeHtml(input) : '（空白）'}</div>
      <div class="verdict">${correct ? '正確' : '再看一次'}</div>
      <div class="answer">正解：${escapeHtml(it.answer)}</div>
      <div class="source">出處：${escapeHtml(it.source_ref)}</div>
      ${correct ? '' : '<button id="also-ok">我這樣寫也對</button>'}
      <button id="next">下一題</button>`;

    let advanced = false;
    const goNext = () => {
      if (advanced) return; // 見下方：click 與 keyup 兩條路徑都可能觸發，只能真的前進一次
      advanced = true;
      idx += 1;
      showItem();
    };
    const nextBtn = host.querySelector('#next');
    nextBtn.onclick = goNext;

    // 修正 H：送出答案（Enter，keydown）之後，再按一次 Enter 要能直接進下一題。
    // 讓「下一題」按鈕拿到焦點，瀏覽器對已聚焦的 <button> 本來就會把 Enter
    // 轉成 click，這是主要機制；下面另外補一個 keyup 監聽只是保底。
    // 兩個關鍵防護，避免「送出時按下的那次 Enter」被這個剛畫出來的結果畫面
    // 直接接住、讓使用者根本來不及看到答案就跳題：
    //   1. 監聽 keyup（送出用的是 keydown）——同一次按鍵才不會被同一個
    //      handler 處理兩次。
    //   2. 監聽器延後到下一個事件迴圈（setTimeout 0）才掛上，且只掛在
    //      host 這個容器上（不是 document）——就算那次按鍵殘留的 keyup
    //      真的還沒發生，它的目標也是已經被換掉、離開 host 的舊輸入框，
    //      事件不會冒泡到這裡。
    nextBtn.focus();
    setTimeout(() => {
      host.addEventListener('keyup', function onKeyup(e) {
        if (e.key !== 'Enter') return;
        host.removeEventListener('keyup', onKeyup);
        goNext();
      });
    }, 0);

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
