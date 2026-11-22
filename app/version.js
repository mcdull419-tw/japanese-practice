// 程式版本，顯示在設定區。必須與 sw.js 的 CACHE 後綴一致（tests/app/test_sw.js 把關），
// 這樣畫面上的「版本」與「快取」兩個數字不一致時，就知道手機卡在舊版。
// 每次發佈要一起改這裡與 sw.js 的 CACHE。
export const APP_VERSION = 'v9';
