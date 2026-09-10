import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments


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


if __name__ == "__main__":
    unittest.main()
