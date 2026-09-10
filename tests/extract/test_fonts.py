import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fonts import font_encodings, decode_hex


class TestFonts(unittest.TestCase):
    def test_lesson07_page1_encodings(self):
        """實測：07.pdf 的 TT2 是 MSGothic/90ms-RKSJ-H，TT4 是 SimSun/GBK-EUC-H。"""
        doc = PDFDoc.from_path("07.pdf")
        enc = font_encodings(doc, doc.pages[0])
        self.assertEqual(enc["TT2"], "cp932")
        self.assertEqual(enc["TT4"], "gb18030")

    def test_decode_japanese(self):
        self.assertEqual(decode_hex("82b182c682ce", "cp932"), "ことば")

    def test_decode_chinese(self):
        self.assertEqual(decode_hex("b5daa3b1d56e", "gb18030"), "第１課")

    def test_all_lessons_have_both_encodings(self):
        """1~15 課每一課都必須同時偵測到日文與中文字型，否則必有一半內容遺失。"""
        for n in range(1, 16):
            doc = PDFDoc.from_path("%02d.pdf" % n)
            found = set()
            for page in doc.pages:
                found.update(font_encodings(doc, page).values())
            self.assertIn("cp932", found, "第 %d 課缺日文字型" % n)
            self.assertIn("gb18030", found, "第 %d 課缺中文字型" % n)


if __name__ == "__main__":
    unittest.main()
