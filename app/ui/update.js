/**
 * 「有新版，點此更新」。
 *
 * 離線快取的特性是：打開 app 時畫面先用舊檔，新版在背景下載好後要等下一次
 * 開啟才會生效；iPhone 主畫面的 app 又很少真的被關掉，使用者可能很久都停在舊版
 * 卻毫無跡象。這裡在新版準備好時主動提示。
 *
 * 不自動重新整理：使用者可能正在作答，頁面突然重載會丟掉那一題。
 */

/**
 * 新的 Service Worker 接手時呼叫 onUpdate（只呼叫一次）。
 *
 * 必須在 register() 之前呼叫，才能正確判斷「進來時已經有控制者」：
 * 第一次安裝時 sw.js 也會 clients.claim() 而觸發 controllerchange，但那是
 * 首次安裝不是更新，不該提示。
 */
export function watchForUpdate(container, onUpdate) {
  if (!container) return;
  const hadController = !!container.controller;
  let notified = false;
  container.addEventListener('controllerchange', () => {
    if (!hadController || notified) return;
    notified = true;
    onUpdate();
  });
}

/**
 * 回到前景時主動問一次有沒有新版。瀏覽器只在載入頁面時檢查，而主畫面 app
 * 常常整天停在背景、不重新載入，不主動問就永遠發現不了。
 */
export function checkWhenVisible(doc, registration) {
  if (!registration) return;
  doc.addEventListener('visibilitychange', () => {
    if (doc.visibilityState === 'visible') registration.update().catch(() => {});
  });
}

export function showUpdateBanner(doc, reload) {
  if (doc.querySelector('#update-banner')) return;
  const bar = doc.createElement('button');
  bar.id = 'update-banner';
  bar.textContent = '有新版，點此更新';
  bar.style.cssText = 'position:fixed;left:16px;right:16px;bottom:max(16px,env(safe-area-inset-bottom));'
    + 'z-index:10;margin:0;padding:14px;font-size:1rem;box-shadow:0 2px 10px rgba(0,0,0,.3)';
  bar.onclick = reload;
  doc.body.appendChild(bar);
}
