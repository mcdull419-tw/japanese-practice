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
                          "zh": "剪，切", "usage": None, "group": None})

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

    def test_no_group_marker_in_lessons_without_verb_classification(self):
        """07 課沒有動詞分類標記，全部單字的 group 都應該是 None。"""
        for v in self.vocab:
            self.assertIsNone(v["group"], "07 課第 %d 筆不應該有 group" % v["no"])


class TestVocabVerbGroup(unittest.TestCase):
    """14 課開始課本用羅馬數字標註動詞分類（Ⅰ／Ⅱ／Ⅲ類），動詞變化練
    習需要這個資訊，必須抽成獨立欄位，不能留在 kana 裡當雜訊。"""

    @classmethod
    def setUpClass(cls):
        lines = group_lines(extract_fragments(PDFDoc.from_path("14.pdf")))
        section = [s for s in split_sections(lines) if s.name == "ことば"][0]
        cls.vocab = parse_vocab(section)
        cls.by_no = {v["no"]: v for v in cls.vocab}

    def test_group_ii_extracted_and_removed_from_kana(self):
        """第 1 筆「つけます Ⅱ」：group 應為 "II"，kana 不應含羅馬數字。"""
        v = self.by_no[1]
        self.assertEqual(v["kana"], "つけます")
        self.assertEqual(v["group"], "II")
        self.assertIsNone(v["kanji"])

    def test_group_i_extracted_and_removed_from_kana(self):
        """第 2 筆「けします Ⅰ消します」：group 應為 "I"，kana 不應含羅馬數字。"""
        v = self.by_no[2]
        self.assertEqual(v["kana"], "けします")
        self.assertEqual(v["group"], "I")
        self.assertEqual(v["kanji"], "消します")

    def test_group_iii_extracted(self):
        """第 18 筆「コピーします Ⅲ」：group 應為 "III"。"""
        v = self.by_no[18]
        self.assertEqual(v["kana"], "コピーします")
        self.assertEqual(v["group"], "III")

    def test_kana_has_no_leading_or_trailing_whitespace(self):
        """全課 kana 欄位不應有前後空白殘留（見任務要求 2）。"""
        for v in self.vocab:
            self.assertEqual(v["kana"], v["kana"].strip(),
                              "第 %d 筆 kana 有前後空白殘留：%r" % (v["no"], v["kana"]))


if __name__ == "__main__":
    unittest.main()
