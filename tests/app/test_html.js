import { test } from 'node:test';
import assert from 'node:assert/strict';
import { escapeHtml, rubyHtml } from '../../app/ui/html.js';

test('escapeHtml 轉義五個危險字元', () => {
  assert.equal(escapeHtml(`<a href="x">&'</a>`),
    '&lt;a href=&quot;x&quot;&gt;&amp;&#39;&lt;/a&gt;');
});

test('rubyHtml 組出 ruby 標籤', () => {
  const tokens = [
    { t: 'ruby', base: '手紙', kana: 'てがみ' },
    { t: 'text', s: 'を 書きます。' },
  ];
  assert.equal(rubyHtml(tokens), '<ruby>手紙<rt>てがみ</rt></ruby>を 書きます。');
});

test('hideRt 時不產生 rt 元素（答案不得存在於 DOM 中）', () => {
  const tokens = [{ t: 'ruby', base: '手紙', kana: 'てがみ' }];
  const html = rubyHtml(tokens, { hideRt: true });
  assert.equal(html, '手紙');
  assert.ok(!html.includes('てがみ'), '讀音不得出現在輸出中');
});

test('rubyHtml 一律轉義文字內容', () => {
  const tokens = [{ t: 'text', s: '<script>' }, { t: 'ruby', base: '<b>', kana: '<i>' }];
  const html = rubyHtml(tokens);
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(html.includes('<ruby>&lt;b&gt;<rt>&lt;i&gt;</rt></ruby>'));
});

test('換行轉成 br，讓代入題的多行題幹不擠成一行', () => {
  assert.equal(rubyHtml([{ t: 'text', s: 'a\nb' }]), 'a<br>b');
});
