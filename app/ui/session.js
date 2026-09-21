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

    // 修正 H（修正過的版本）：送出答案（Enter）之後，要再按一次 Enter 才能
    // 進下一題；不能被送出那次按鍵的「放開」尾段接住。
    //
    // 舊版監聽 keyup 並用 setTimeout(0) 延後掛上，理由是「這樣才躲得掉
    // 送出用的那次 Enter」——這個理由是錯的，已用 Playwright 模擬真人按鍵
    // （down → 等 120ms → up）實測重現：真人按住 Enter 常常是 60～150ms
    // 才放開，setTimeout(0) 的 macrotask 早就跑完、keyup 監聽器早就掛好，
    // 放開時的 keyup 目標又是剛剛 focus() 的 #next（在 host 內部，不是
    // 已離開 host 的舊輸入框），事件會冒泡到 host，導致結果畫面被同一次
    // 按鍵直接跳過。
    //
    // 改監聽 keydown 才是真的安全：送出當下那個 keydown 在同步的事件派送
    // 過程中就已經完整跑完（JS 單執行緒，不需要、也不能用 setTimeout 延後
    // 才「躲開」），此刻才用 addEventListener 掛上的 keydown 監聽器不可能
    // 收到那個已經處理完的事件；使用者必須真的再按一次鍵盤，才會有下一個
    // keydown 送過來。
    //
    // 保留 advanced 旗標的理由不變：nextBtn.focus() 讓「下一題」按鈕拿到
    // 焦點後，瀏覽器對已聚焦的 <button> 收到 Enter keydown 時，本來就會
    // 原生地額外觸發一次 click——同一次按鍵因此會同時走 keydown 監聽與
    // click 兩條路徑，advanced 保證 goNext() 只真正前進一次。
    nextBtn.focus();
    host.addEventListener('keydown', function onKeydown(e) {
      if (e.key !== 'Enter') return;
      host.removeEventListener('keydown', onKeydown);
      goNext();
    });

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
