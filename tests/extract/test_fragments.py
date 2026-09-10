import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments, page_fragments


class TestFragments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frags = extract_fragments(PDFDoc.from_path("07.pdf"))

    def test_has_kotoba_heading(self):
        heads = [f for f in self.frags if f.text.strip() == "ことば"]
        self.assertTrue(heads, "找不到『ことば』標題")

    def test_first_vocab_entry_present(self):
        texts = "".join(f.text for f in self.frags if f.page == 1)
        for expected in ("きります", "切ります", "剪"):
            self.assertIn(expected, texts)

    def test_fragments_carry_coordinates(self):
        for f in self.frags[:50]:
            self.assertIsInstance(f.x, float)
            self.assertIsInstance(f.y, float)
            self.assertGreater(f.size, 0.0)

    def test_ruby_fragments_are_smaller(self):
        """振假名為 4.8pt 小字；正文為 10pt 以上。兩種字級必須都存在。"""
        sizes = {round(f.size, 1) for f in self.frags}
        self.assertTrue(any(s <= 6.0 for s in sizes), "找不到小字級（振假名）")
        self.assertTrue(any(s >= 10.0 for s in sizes), "找不到正文字級")

    def test_no_misdecoding_fingerprint(self):
        """Shift-JIS 被誤讀為 GB18030 會產生這些罕見漢字。"""
        text = "".join(f.text for f in self.frags)
        for bad in "偁偄偆偊偍偐偑偒偓偔偕偖偗偘偙偠偡偣偤偦偨偩偪偭偮偯偰偱偲偵偼":
            self.assertNotIn(bad, text, "偵測到誤解碼指紋：%s" % bad)


class _MockPage:
    """Synthetic Page for pinning Td/TD coordinate arithmetic in isolation."""

    def __init__(self, number, content, resources):
        self.number = number
        self.content = content
        self.resources = resources


class _MockPDFDoc:
    """Synthetic PDFDoc backing _MockPage's /Font resource lookup."""

    def __init__(self, objects):
        self._objects = objects

    def get_object(self, num):
        return self._objects.get(num, b"")


class TestFragmentCoordinates(unittest.TestCase):
    """回歸測試：鎖定 Td/TD 位移的座標數值，不只檢查子字串是否存在。

    這兩個測試專門防範兩種「五個原始測試完全抓不到」的退化：
    (a) Td/TD 分支未觸發（例如誤用 `m.lastgroup` 導致 dispatch 失效）；
    (b) Td/TD 位移未依 PDF 規格乘上文字矩陣縮放（`x += tx` 而非
        `x += tx * self.a`）。
    兩種退化都會讓 fragment 疊在同一座標，但文字子字串序列不變，
    `test_first_vocab_entry_present` 那類測試因此無感。
    """

    def test_td_scales_by_text_matrix(self):
        """人工構造的最小內容流：BT → Tm → Td → 兩個 Tj → ET。

        數字直接取自 07.pdf 第 3 頁的實測運算子（13.2pt 字級、
        tx=-4.1818 的 TD）：依規格縮放後應落在 x=12.0（該頁其他 Tm
        反覆設定的左邊界），不縮放則會是任意數字 67.2-4.1818≈63.02。
        """
        content = (
            b"BT\n"
            b"/TT2 1 Tf\n"
            b"13.2 0 0 13.2 67.2 829.46 Tm\n"
            b"<82b1>Tj\n"
            b"-4.1818 0 TD\n"
            b"<82c6>Tj\n"
            b"ET\n"
        )
        resources = b"<< /Font << /TT2 1 0 R >> >>"
        objects = {1: b"<< /Type /Font /BaseFont /MSGothic >>"}
        page = _MockPage(number=1, content=content, resources=resources)
        doc = _MockPDFDoc(objects)

        frags = page_fragments(doc, page)

        self.assertEqual(len(frags), 2)
        self.assertAlmostEqual(frags[0].x, 67.2, places=2)
        self.assertAlmostEqual(frags[0].y, 829.46, places=2)
        self.assertAlmostEqual(frags[1].x, 12.0, places=2)
        self.assertAlmostEqual(frags[1].y, 829.46, places=2)

    def test_lesson07_vocab_row_columns_align(self):
        """實測 07.pdf 第 1 頁第一個單字列：日文／假名／中文三欄的 x 座標。

        三個欄位同列（y 相同），x 座標彼此分開且與實測值吻合——這是
        「欄位切分」模組唯一能依賴的不變量。若座標退化成疊在同一點，
        這裡會直接爆炸。
        """
        frags = extract_fragments(PDFDoc.from_path("07.pdf"))
        by_text = {
            f.text.strip(): f
            for f in frags
            if f.page == 1 and f.text.strip() in ("きります", "切ります", "剪，切")
        }
        self.assertIn("きります", by_text)
        self.assertIn("切ります", by_text)
        self.assertIn("剪，切", by_text)

        kanji = by_text["きります"]
        chinese_verb = by_text["切ります"]
        chinese_gloss = by_text["剪，切"]

        self.assertAlmostEqual(kanji.x, 53.4, places=1)
        self.assertAlmostEqual(chinese_verb.x, 166.2, places=1)
        self.assertAlmostEqual(chinese_gloss.x, 497.4, places=1)

        # 同一列，y 應相同（在浮點誤差範圍內）。
        self.assertAlmostEqual(kanji.y, 768.26, places=1)
        self.assertAlmostEqual(chinese_verb.y, kanji.y, places=6)
        self.assertAlmostEqual(chinese_gloss.y, kanji.y, places=6)


if __name__ == "__main__":
    unittest.main()
