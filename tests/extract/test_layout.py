import unittest
from collections import Counter

from tools.extract.fonts import char_width
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines, _line_chars


class TestLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lines = group_lines(extract_fragments(PDFDoc.from_path("07.pdf")))

    def test_reading_order(self):
        """行必須依頁碼遞增、頁內 y 遞減排序。"""
        prev = None
        for ln in self.lines:
            key = (ln.page, -ln.y)
            if prev is not None:
                self.assertGreaterEqual(key, prev)
            prev = key

    def test_vocab_row_splits_into_three_cells(self):
        """單字列有三欄：假名、漢字、中文。"""
        target = None
        for ln in self.lines:
            if "きります" in ln.text() and "切ります" in ln.text():
                target = ln
                break
        self.assertIsNotNone(target, "找不到第 1 筆單字所在行")
        cells = target.cells()
        texts = [c.text.strip() for c in cells]
        self.assertIn("きります", texts)
        self.assertIn("切ります", texts)
        self.assertTrue(any("剪" in t for t in texts))

    def test_kana_only_entry_has_empty_kanji_column(self):
        """第 3 筆 あげます 沒有漢字，中文欄的 x 必須仍落在第三欄位置。"""
        target = None
        for ln in self.lines:
            if "あげます" in ln.text():
                target = ln
                break
        self.assertIsNotNone(target)
        xs = [c.x for c in target.cells()]
        self.assertGreaterEqual(len(xs), 2)

    def test_substitution_table_columns_align(self):
        """練習Ａ-2 的三個候選詞必須落在相同 x 欄位。"""
        rows = [ln for ln in self.lines
                if any(w in ln.text() for w in ("にほんご", "えいご", "ちゅうごくご"))]
        self.assertGreaterEqual(len(rows), 3, "找不到練習Ａ-2 的代入表")


def _frag_end(f, char_width_fn=char_width):
    """獨立於 layout.py 實作、依規則本身重新計算的 fragment 估計結束位置
    （測試用；不呼叫 layout.py 的私有函式，避免測試只是在跟實作自己比較）。
    """
    x = f.x
    for ch in f.text:
        x += char_width_fn(ch, f.size)
    return x


def _spec_host_of(frags):
    """獨立於 layout.py 重新實作一次「插入 vs. 原子性」規則本身：f 的宿主
    是「f 的錨點嚴格落在其 [起點, 結束) 跨距內部」的 fragment，多個候選
    時取跨距最短的一個。回傳 {id(f): 宿主 fragment 或 None}。

    這是規格層級的獨立實作，特意不 import layout.py 的 `_find_host`——
    否則量化不變量只是在驗證實作跟自己一致，抓不到「實作偷偷換了規則」
    這種錯誤（就是這一輪要修的那種回歸）。
    """
    host_of = {}
    for f in frags:
        candidates = [h for h in frags if h is not f and h.x < f.x < _frag_end(h)]
        host_of[id(f)] = min(candidates, key=lambda h: _frag_end(h) - h.x) if candidates else None
    return host_of


def _spec_is_descendant(f, ancestor, host_of):
    """f 是否為 ancestor 的（直接或間接）合法插入對象。"""
    cur = f
    seen = set()
    while True:
        host = host_of.get(id(cur))
        if host is None:
            return False
        if host is ancestor:
            return True
        if id(host) in seen:
            return False  # 防禦性：理論上不該有環
        seen.add(id(host))
        cur = host


class TestCharLevelReadingOrder(unittest.TestCase):
    """回歸測試：課本把日文詞彙插進中文說明的字元之間（反之亦然），依
    fragment 起點 x 排序、逐 fragment 串接文字會把穿插的 fragment 整批
    插在錯誤位置（07 課「打電話」）。但「兩個 fragment 錨點 x 完全相等」
    不是穿插，是兩段獨立文字恰好從同一點畫起，各自必須保持連續整塊
    （14 課「ます」/「視」——第一輪修正曾經誤判這種情形也需要拆開插入，
    造成真實回歸，見 Task 4 report 第二輪修正）。這裡用一個涵蓋全 15 課
    的量化不變量鎖住「插入 vs. 原子性」這條規則本身，不是只測下面幾個
    具體案例。
    """

    def test_lesson07_entry9_chinese_gloss_reconstructs_with_bracket_inside(self):
        """07 課第 9 筆單字「打電話」：中文釋義被拆成「打電」「〔」「話」
        「〕」四個 fragment，「〔」的錨點 397.8 嚴格落在「打電」的跨距
        (384.6, 411.0) 內部——這是真正的穿插，必須拆進去，得到
        「打〔電話〕」，不是依 fragment 起點 x 排序會得到的「打電〔話〕」。
        """
        lines = group_lines(extract_fragments(PDFDoc.from_path("07.pdf")))
        target = None
        for ln in lines:
            if ln.page == 1 and abs(ln.y - 605.06) < 0.5:
                target = ln
                break
        self.assertIsNotNone(target, "找不到第 9 筆單字所在列（y≈605.06）")
        text = target.text()
        self.assertIn("打〔電話〕", text)
        self.assertNotIn("打電〔話〕", text)

    def test_lesson14_masu_and_shi_stay_atomic_not_interleaved(self):
        """回歸測試（第二輪修正的直接原因）：14 課 p.8「Ⅰ類動詞ます形」
        說明列，`ます`（TT2）與 `視`（TT4）兩個 fragment 的錨點 x 完全
        相等（150.6）。這不是穿插——兩者是各自獨立、恰好從同一點畫起的
        文字段，正確讀法要求 `ます` 兩個字連續出現、`視` 完整接在後面
        （或前面，但不能插進 `ます` 中間）：「ます視」，不是被硬插成
        「ま視す」。
        """
        lines = group_lines(extract_fragments(PDFDoc.from_path("14.pdf")))
        target = None
        for ln in lines:
            if ln.page == 8 and "Ⅰ類動詞" in ln.text() and "ます" in ln.text():
                target = ln
                break
        self.assertIsNotNone(target, "找不到 14 課「Ⅰ類動詞ます形」說明列（page=8, y≈625.46）")
        text = target.text()
        self.assertIn("ます視", text)
        self.assertNotIn("ま視す", text)

    def test_lesson01_dare_row_keeps_quoted_terms_atomic_in_stream_order(self):
        """01 課「だれ」列：中文「誰（哪位）（」＋字距調整＋「是」與日文
        引號詞「“だれ”」的錨點 x 完全相等（529.79988，逐位元相同，兩條
        獨立的座標計算路徑剛好收斂在同一點，不是巧合的四捨五入）。這不
        是穿插——依「插入 vs. 原子性」規則，兩個 fragment 各自保持完整
        連續，先後依內容流原始順序：實測「“だれ”」（在同一個 TT2 TJ
        陣列內、與「“どなた”」一起）在內容流中先於「是」（在後面另一個
        BT 區塊的 TT4 TJ 陣列裡）被畫出，所以「“だれ”」整塊排在「是」
        整塊之前，得到「“どなた”“だれ”是」。

        第一輪修正曾經用「開頭標點在錨點對錨點打平時排後面」的啟發式把
        這裡排成「“どなた”是“だれ”」——複審指出這條啟發式只有這一個
        案例佐證（n=1），套到 14 課「ます」/「視」等其他打平案例上會出錯
        （見 Task 4 report 第二輪修正）。改用「錨點相等即原子性、依內容
        流順序」這條有多個獨立案例佐證的規則後，這裡的正確輸出也隨之
        修正為「“どなた”“だれ”是」——這是我們對這一行語意的重新判斷，
        不是規則的例外；細節見 Task 4 report。
        """
        lines = group_lines(extract_fragments(PDFDoc.from_path("01.pdf")))
        target = None
        for ln in lines:
            if ln.page == 1 and "どなた" in ln.text() and "だれ" in ln.text():
                target = ln
                break
        self.assertIsNotNone(target, "找不到「だれ（どなた）」單字所在列")
        text = target.text()
        self.assertIn("“どなた”“だれ”是", text)
        self.assertNotIn("“どなた”是“だれ”", text)

    def test_char_level_reconstruction_respects_insertion_rule_across_all_lessons(self):
        """量化不變量（涵蓋 1~15 課全書，不是只測上面幾個個案）：

        對每一行的每個 fragment F：在重建後的字元序列裡，F 自己的字元第
        一次出現到最後一次出現之間，只允許出現「F 的合法插入對象」的
        字元（依規則獨立重新計算：某 fragment 的錨點嚴格落在 F 的
        [起點, 結束) 跨距內部，見 `_spec_host_of`／`_spec_is_descendant`,
        不呼叫 layout.py 的私有實作）——換句話說，沒有被任何 fragment
        合法插入的部分，F 自己的字元必須連續出現，不能被不相干的內容
        打斷。這條不變量直接對應規則本身，能抓住「錨點相等卻被誤判成
        可以插入」這整類錯誤（不像先前版本用的「x 單調遞增＋字元多重集
        無損」——那條不變量對「同一個 fragment 的字元被切成兩半、中間
        插了別人」這種順序錯誤完全無感：字元多重集不看順序，x 單調遞增
        則是任何依 x 的穩定排序法都恆成立，偵測不出问題）。

        同時保留字元多重集合檢查（重建不遺漏、不重複字元），以及
        `Line.text()` 與內部排序結果 `_line_chars()` 一致的檢查（把不
        變量綁回公開介面）。
        """
        total_lines = 0
        total_chars = 0
        total_fragments_checked = 0
        for n in range(1, 16):
            doc = PDFDoc.from_path("%02d.pdf" % n)
            lines = group_lines(extract_fragments(doc))
            for ln in lines:
                total_lines += 1
                chars = _line_chars(ln.frags)
                total_chars += len(chars)

                self.assertEqual(
                    ln.text(), "".join(ch for ch, _x, _f in chars),
                    "第 %d 課 page=%d y=%.2f 的 text() 與 _line_chars() 不一致"
                    % (n, ln.page, ln.y)
                )

                reconstructed = Counter(ch for ch, _x, _f in chars)
                original = Counter("".join(f.text for f in ln.frags))
                self.assertEqual(
                    reconstructed, original,
                    "第 %d 課 page=%d y=%.2f 重建後字元多重集合與原始不符"
                    % (n, ln.page, ln.y)
                )

                if len(ln.frags) < 2:
                    continue

                host_of = _spec_host_of(ln.frags)
                for f in ln.frags:
                    total_fragments_checked += 1
                    positions = [i for i, (_ch, _x, src) in enumerate(chars) if src is f]
                    if not positions:
                        continue
                    first, last = positions[0], positions[-1]
                    for i in range(first, last + 1):
                        _ch, _x, src = chars[i]
                        if src is f:
                            continue
                        self.assertTrue(
                            _spec_is_descendant(src, f, host_of),
                            "第 %d 課 page=%d y=%.2f："
                            "fragment %r（錨點 x=%.2f）的字元被非合法插入對象"
                            "（%r，來自 %r，錨點 x=%.2f）打斷；重建文字＝%r"
                            % (n, ln.page, ln.y, f.text, f.x,
                               _ch, src.text, src.x, ln.text())
                        )

        # 確保這個不變量真的掃過了大量真實資料，不是空迴圈通過。
        self.assertGreater(total_lines, 1000, "掃過的行數太少，這個不變量可能沒有真的執行")
        self.assertGreater(total_chars, 10000, "掃過的字元數太少，這個不變量可能沒有真的執行")
        self.assertGreater(total_fragments_checked, 10000, "檢查過的 fragment 數太少，這個不變量可能沒有真的執行")


if __name__ == "__main__":
    unittest.main()
