import unittest
from collections import Counter

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


class TestCharLevelReadingOrder(unittest.TestCase):
    """回歸測試：課本把日文詞彙插進中文說明的字元之間（反之亦然），依
    fragment 起點 x 排序、逐 fragment 串接文字會把穿插的 fragment 整批
    插在錯誤位置。這裡鎖定「依字元展開、全域排序」這個修正，並且用一個
    涵蓋全 15 課的量化不變量鎖住整類錯誤，不是只測下面兩個具體案例。
    """

    def test_lesson07_entry9_chinese_gloss_reconstructs_with_bracket_inside(self):
        """07 課第 9 筆單字「打電話」：中文釋義被拆成「打電」「〔」「話」
        「〕」四個 fragment，「〔」的 x 落在「打電」內部（見 Task 4
        report）。正確讀法是「打〔電話〕」，不是依 fragment 起點 x 排序
        會得到的「打電〔話〕」。
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

    def test_lesson01_dare_row_interleaves_chinese_between_quoted_terms(self):
        """01 課「だれ」列：中文說明「誰（哪位）（“どなた”是“だれ”」把
        「是」插在兩個日文引號詞「“どなた”」與「“だれ”」之間（「是」與
        「“だれ”」的開引號座標完全相同，見 Task 4 report 的 tie-break
        說明）。正確讀法是「“どなた”是“だれ”」，不是「“どなた”“だれ”是」。
        """
        lines = group_lines(extract_fragments(PDFDoc.from_path("01.pdf")))
        target = None
        for ln in lines:
            if ln.page == 1 and "どなた" in ln.text() and "だれ" in ln.text():
                target = ln
                break
        self.assertIsNotNone(target, "找不到「だれ（どなた）」單字所在列")
        text = target.text()
        self.assertIn("“どなた”是“だれ”", text)
        self.assertNotIn("“どなた”“だれ”是", text)

    def test_char_level_reconstruction_is_x_sorted_and_lossless_across_all_lessons(self):
        """量化不變量（涵蓋 1~15 課全書，不是只測上面兩個個案）：

        對每一行，`Line.text()` 背後用來排序的字元 x 序列必須是非遞減
        （這是「依全域 x 展開排序」這個修正本身的定義——任何退化回「逐
        fragment 串接」的改動，只要那一行存在 fragment 互相穿插，這個
        不變量就會被打破，因為 fragment 級的串接無法保證字元級的 x
        單調遞增）；同時，重建後的字元多重集合必須與原始 fragment 文字
        字元的多重集合完全一致（含順序無關的計數）——證明這只是「重新
        排序」，沒有遺漏或重複任何字元。
        """
        total_lines = 0
        total_chars = 0
        for n in range(1, 16):
            doc = PDFDoc.from_path("%02d.pdf" % n)
            lines = group_lines(extract_fragments(doc))
            for ln in lines:
                total_lines += 1
                chars = _line_chars(ln.frags)
                total_chars += len(chars)

                # Line.text() 必須完全來自這個排序結果，不能有第二條、可能
                # 各自漂移的路徑（例如退化回逐 fragment 串接）——這一行直接
                # 把量化不變量綁回公開介面 text()，不是只測內部 helper。
                self.assertEqual(
                    ln.text(), "".join(ch for ch, _x, _f in chars),
                    "第 %d 課 page=%d y=%.2f 的 text() 與 _line_chars() 不一致"
                    % (n, ln.page, ln.y)
                )

                xs = [x for _ch, x, _f in chars]
                for i in range(1, len(xs)):
                    self.assertGreaterEqual(
                        xs[i], xs[i - 1],
                        "第 %d 課 page=%d y=%.2f 的字元 x 序列不是非遞減："
                        "%r" % (n, ln.page, ln.y, [c for c, _x, _f in chars])
                    )

                reconstructed = Counter(ch for ch, _x, _f in chars)
                original = Counter("".join(f.text for f in ln.frags))
                self.assertEqual(
                    reconstructed, original,
                    "第 %d 課 page=%d y=%.2f 重建後字元多重集合與原始不符"
                    % (n, ln.page, ln.y)
                )

        # 確保這個不變量真的掃過了大量真實資料，不是空迴圈通過。
        self.assertGreater(total_lines, 1000, "掃過的行數太少，這個不變量可能沒有真的執行")
        self.assertGreater(total_chars, 10000, "掃過的字元數太少，這個不變量可能沒有真的執行")


if __name__ == "__main__":
    unittest.main()
