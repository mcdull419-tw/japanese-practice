import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections
from tools.extract.vocab import parse_vocab


class TestVocab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lines = group_lines(extract_fragments(PDFDoc.from_path("07.pdf")))
        section = [s for s in split_sections(lines) if s.name == "ことば"][0]
        cls.vocab = parse_vocab(section)
        cls.by_no = {v["no"]: v for v in cls.vocab}

    def test_count(self):
        """第 7 課實測有 38 筆單字。"""
        self.assertEqual(len(self.vocab), 38)

    def test_numbers_are_contiguous(self):
        self.assertEqual(sorted(self.by_no), list(range(1, 39)))

    def test_entry_with_kanji(self):
        self.assertEqual(self.by_no[1],
                         {"no": 1, "kana": "きります", "kanji": "切ります",
                          "zh": "剪，切", "usage": None})

    def test_entry_without_kanji(self):
        v = self.by_no[3]
        self.assertEqual(v["kana"], "あげます")
        self.assertIsNone(v["kanji"])
        self.assertIn("給", v["zh"])

    def test_tight_spaced_entry(self):
        """第 10 筆 て/手 是單一字串靠字距撐開，須以第一個表意文字為切點。"""
        v = self.by_no[10]
        self.assertEqual(v["kana"], "て")
        self.assertEqual(v["kanji"], "手")

    def test_usage_subline_preserved(self):
        """第 9 筆 かけます 下方有 ［でんわを～］／［電話を～］，原型整行遺失。"""
        v = self.by_no[9]
        self.assertEqual(v["kana"], "かけます")
        self.assertIsNotNone(v["usage"], "搭配用法子行遺失")
        self.assertIn("でんわ", v["usage"]["kana"])
        self.assertIn("電話", v["usage"]["kanji"])

    def test_chinese_brackets_not_stripped(self):
        """第 9 筆中文為『打〔電話〕』，角括號不可被當成偽漢字過濾掉。"""
        self.assertIn("〔", self.by_no[9]["zh"])

    def test_katakana_entries(self):
        self.assertEqual(self.by_no[21]["kana"], "セロテープ")
        self.assertIsNone(self.by_no[21]["kanji"])
        self.assertIn("膠帶", self.by_no[21]["zh"])


if __name__ == "__main__":
    unittest.main()
