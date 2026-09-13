import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections
from tools.extract.patterns import parse_pattern_tables, parse_drills


class TestPatterns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lines = group_lines(extract_fragments(PDFDoc.from_path("07.pdf")))
        cls.sections = {s.name: s for s in split_sections(lines)}
        cls.tables = parse_pattern_tables(cls.sections["練習Ａ"], 7)
        cls.drills = parse_drills(cls.sections["練習Ｂ"], 7)

    def test_table_count(self):
        """第 7 課練習Ａ 實測有 6 張代入表。"""
        self.assertEqual(len(self.tables), 6)

    def test_single_slot_table(self):
        """練習Ａ-2：わたしは にほんご／えいご／ちゅうごくご で レポートを 書きます。"""
        t = self.tables[1]
        values = [v for vals in t["slots"].values() for v in vals]
        for expected in ("にほんご", "えいご", "ちゅうごくご"):
            self.assertIn(expected, values)

    def test_two_slot_table_rows_are_paired(self):
        """練習Ａ-1 有兩個槽位，同列詞彙必須成組，不可跨列自由組合。"""
        t = self.tables[0]
        self.assertEqual(len(t["slots"]), 2, "應偵測到兩個槽位")
        self.assertEqual(len(t["rows"]), 3, "應有三列")
        slot_names = sorted(t["slots"])
        first = t["slots"][slot_names[0]]
        second = t["slots"][slot_names[1]]
        self.assertIn("日本人", first)
        self.assertIn("はし", second)
        idx_jp = first.index("日本人")
        row = [r for r in t["rows"] if r[0] == idx_jp][0]
        self.assertEqual(second[row[1]], "はし", "日本人 必須配 はし")

    def test_template_has_placeholders(self):
        for t in self.tables:
            self.assertIn("{", t["template"], "模板缺少槽位佔位符：%s" % t["id"])

    def test_ids_stable(self):
        self.assertEqual(self.tables[0]["id"], "L07-A1")
        self.assertEqual([t["id"] for t in self.tables],
                         ["L07-A%d" % i for i in range(1, 7)])

    def test_drill_count(self):
        """第 7 課練習Ｂ 實測有 7 題。"""
        self.assertEqual(len(self.drills), 7)

    def test_drill_item_order(self):
        """原型的 bug：同列的 1) 2) 順序錯亂，輸出成『2) 教えます 1) 貸します』。"""
        d = [x for x in self.drills if x["id"] == "L07-B3"][0]
        self.assertEqual(d["items"][:2], ["貸します", "教えます"])


if __name__ == "__main__":
    unittest.main()
