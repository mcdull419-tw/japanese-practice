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

/**
 * 設定區顯示的版本資訊：程式版本，以及這支手機目前存的離線快取版本。
 * 兩者不同就代表舊檔還留在快取裡。
 */
export async function describeVersion(cacheStorage, appVersion) {
  let keys = [];
  try { keys = cacheStorage ? await cacheStorage.keys() : []; } catch { /* 沒有快取就當作空 */ }
  const stored = keys.filter((k) => k.startsWith('jp-practice-')).map((k) => k.replace('jp-practice-', ''));
  const cacheText = stored.length ? stored.join('、') : '無';
  const stale = stored.length > 0 && !(stored.length === 1 && stored[0] === appVersion);
  return `版本 ${appVersion}｜離線快取 ${cacheText}${stale ? '（與程式不符，請按「重新下載最新版」）' : ''}`;
}

/**
 * 「重新下載最新版」：解除 Service Worker、清掉所有離線快取、重新載入。
 * 只動程式快取——學習紀錄在 IndexedDB、設定在 localStorage，這裡完全不碰。
 * 重新載入後會重新註冊並下載最新版。
 */
export async function forceRefresh(win) {
  try {
    const regs = await win.navigator.serviceWorker.getRegistrations();
    await Promise.all(regs.map((r) => r.unregister()));
  } catch { /* 不支援或失敗時，繼續清快取 */ }
  try {
    const keys = await win.caches.keys();
    await Promise.all(keys.map((k) => win.caches.delete(k)));
  } catch { /* 同上 */ }
  win.location.reload();
}
