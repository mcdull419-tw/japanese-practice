import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeSpeaker } from '../../app/core/tts.js';

function fakeSynth(voices = [{ lang: 'ja-JP', name: 'Kyoko' }]) {
  return {
    spoken: [], cancelled: 0,
    getVoices: () => voices,
    speak(u) { this.spoken.push(u); },
    cancel() { this.cancelled += 1; },
  };
}
class FakeUtterance {
  constructor(text) { this.text = text; }
}

test('speak 送出日文語音設定', () => {
  const synth = fakeSynth();
  makeSpeaker(synth, FakeUtterance).speak('手紙を 書きます。');
  assert.equal(synth.spoken.length, 1);
  assert.equal(synth.spoken[0].text, '手紙を 書きます。');
  assert.equal(synth.spoken[0].lang, 'ja-JP');
  assert.equal(synth.spoken[0].rate, 0.9);
});

test('speak 前先 cancel，避免上一題的語音疊上來', () => {
  const synth = fakeSynth();
  const sp = makeSpeaker(synth, FakeUtterance);
  sp.speak('あ');
  sp.speak('い');
  assert.equal(synth.cancelled, 2);
});

test('沒有語音合成時 available 為假且 speak 不炸', () => {
  const sp = makeSpeaker(null, FakeUtterance);
  assert.equal(sp.available(), false);
  assert.doesNotThrow(() => sp.speak('あ'));
  assert.doesNotThrow(() => sp.cancel());
});

test('沒有日文語音時 available 為假（不以英文語音唸日文）', () => {
  const sp = makeSpeaker(fakeSynth([{ lang: 'en-US', name: 'Alex' }]), FakeUtterance);
  assert.equal(sp.available(), false);
});

test('getVoices 尚未就緒（回空陣列）時仍視為可用', () => {
  // Chrome 首次呼叫 getVoices 常回空陣列，稍後才非同步填入。
  // 此時判為不可用會讓聽力功能在剛開頁時無故消失。
  assert.equal(makeSpeaker(fakeSynth([]), FakeUtterance).available(), true);
});

test('空字串不送出語音', () => {
  const synth = fakeSynth();
  makeSpeaker(synth, FakeUtterance).speak('');
  assert.equal(synth.spoken.length, 0);
});

test('速率可調', () => {
  const synth = fakeSynth();
  makeSpeaker(synth, FakeUtterance).speak('あ', { rate: 0.6 });
  assert.equal(synth.spoken[0].rate, 0.6);
});
