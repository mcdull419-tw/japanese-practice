/**
 * Web Speech API 的封裝（規格 §6.2：聽力是呈現修飾，不是第五種引擎）。
 *
 * 合成器以參數注入而非直接抓 window.speechSynthesis——core/ 不得出現
 * window／document（規格 §11 的分層要求，Phase 1 已以 grep 驗收）。
 * 注入同時讓這個模組測得到：真的 speechSynthesis 在 Node 裡不存在。
 *
 * 已知限制（規格 §14）：iOS Safari 在鎖屏或切到背景時會暫停 speechSynthesis，
 * 因此循環播放須保持螢幕開啟。UI 明示，不在此處緩解。
 */
export function makeSpeaker(synth, UtteranceCtor) {
  function available() {
    if (!synth || typeof synth.speak !== 'function' || typeof UtteranceCtor !== 'function') {
      return false;
    }
    const voices = typeof synth.getVoices === 'function' ? synth.getVoices() : [];
    // Chrome 首次呼叫 getVoices 常回空陣列，語音清單稍後才非同步填入。
    // 空陣列判為不可用，會讓聽力功能在剛開頁的那幾百毫秒無故消失。
    if (!voices.length) return true;
    return voices.some((v) => (v.lang || '').toLowerCase().startsWith('ja'));
  }

  return {
    available,
    speak(text, { lang = 'ja-JP', rate = 0.9 } = {}) {
      if (!available() || !text) return;
      // 先取消：上一題的語音若還沒唸完，兩段會疊在一起，兩題都聽不清楚。
      synth.cancel();
      const u = new UtteranceCtor(text);
      u.lang = lang;
      u.rate = rate;
      synth.speak(u);
    },
    cancel() {
      if (synth && typeof synth.cancel === 'function') synth.cancel();
    },
  };
}
