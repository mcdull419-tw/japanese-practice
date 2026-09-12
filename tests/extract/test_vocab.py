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

    def test_loanword_verb_has_no_fabricated_kanji(self):
        """第 18 筆「コピーします」是外來語動詞，本來就沒有漢字讀音。

        Task 7 複審修正前：課本用巨大 Tc 把動詞分類羅馬數字「Ⅲ」跟中
        文釋義「影印」的第一個字「影」編碼進同一個 Fragment（文字
        `"Ⅲ影"`），`layout.py` 估計字元位置時把「影」誤判成緊跟在
        「Ⅲ」後面、落入漢字欄，導致題庫會教使用者「コピーします 寫
        作 影します」——不是缺漏，是捏造出一個根本不存在的漢字讀音。
        修正 `fragments.py`（Tc 大到造成真實視覺分離時逐字元拆分）後，
        「影」正確前進到中文欄，kanji 應為 None、zh 應為完整的
        "影印"。"""
        v = self.by_no[18]
        self.assertIsNone(v["kanji"], "外來語動詞不應該有捏造出來的漢字：%r" % v["kanji"])
        self.assertEqual(v["zh"], "影印")

    def test_matsu_verb_kanji_and_zh_not_glued(self):
        """第 6 筆「まちます」：先前 bug 把中文釋義「等待」的「等」字
        黏進漢字欄，變成 kanji='等待ちます'、zh='待'（見模組說明與
        `tools/extract/fragments.py` 模組說明的根因分析）。修正後
        kanji 應為乾淨的「待ちます」，zh 應為完整的「等待」。"""
        v = self.by_no[6]
        self.assertEqual(v["kana"], "まちます")
        self.assertEqual(v["group"], "I")
        self.assertEqual(v["kanji"], "待ちます")
        self.assertEqual(v["zh"], "等待")

    def test_kana_has_no_leading_or_trailing_whitespace(self):
        """全課 kana 欄位不應有前後空白殘留（見任務要求 2）。"""
        for v in self.vocab:
            self.assertEqual(v["kana"], v["kana"].strip(),
                              "第 %d 筆 kana 有前後空白殘留：%r" % (v["no"], v["kana"]))


class TestVocabLesson15TcFix(unittest.TestCase):
    """15 課同樣受課本大 Tc 撐開動詞分類標記與中文釋義首字的根因影響
    （4 筆：#2、7、8、9），這裡鎖住其中最早發現、已算繪核對過視覺位置
    的第 2 筆。"""

    @classmethod
    def setUpClass(cls):
        lines = group_lines(extract_fragments(PDFDoc.from_path("15.pdf")))
        section = [s for s in split_sections(lines) if s.name == "ことば"][0]
        cls.vocab = parse_vocab(section)
        cls.by_no = {v["no"]: v for v in cls.vocab}

    def test_suwarimasu_kanji_and_zh_not_glued(self):
        """第 2 筆「すわります」：算繪 15.pdf 第 1 頁核對過視覺位置，
        正確答案是 kana='すわります'、kanji='座ります'、zh='坐'。修正
        前 kanji 混進了中文釋義的「坐」字（'座ります坐'），zh 變成空
        字串。"""
        v = self.by_no[2]
        self.assertEqual(v["kana"], "すわります")
        self.assertEqual(v["group"], "I")
        self.assertEqual(v["kanji"], "座ります")
        self.assertEqual(v["zh"], "坐")


if __name__ == "__main__":
    unittest.main()
