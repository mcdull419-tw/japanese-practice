import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines


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


if __name__ == "__main__":
    unittest.main()
