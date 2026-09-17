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


class TestDrillCueAnswerLayoutVariants(unittest.TestCase):
    """複審發現：cue／answer 用 `str.partition("→")` 依字串位置切分，
    在兩種課本排版變體下會把內容分進錯的欄位（內容仍在原始文字裡，只
    是欄位裝錯，因此原本的「逐字回查」檢查測不出來）。這裡分別鎖定
    這兩種變體各一個真實案例。"""

    def test_no_arrow_question_answer_format(self):
        """06 課練習Ｂ-7：整段沒有任何『→』符號（『例：いっしょに
        京都へ 行きませんか。』下一行『……ええ、行きましょう。』）。
        原本的 bug：`partition` 找不到分隔符，整段問句被塞進 cue，
        answer 變成空字串。正確行為：沒有可分離的 cue 詞時，cue 應為
        空字串，問句與答案合併進 answer。"""
        lines = group_lines(extract_fragments(PDFDoc.from_path("06.pdf")))
        sections = {s.name: s for s in split_sections(lines)}
        drills = parse_drills(sections["練習Ｂ"], 6)
        d = [x for x in drills if x["id"] == "L06-B7"][0]
        self.assertEqual(d["model_cue"], "")
        self.assertIn("いっしょに 京都へ 行きませんか。", d["model_answer"])
        self.assertIn("ええ、行きましょう。", d["model_answer"])

    def test_answer_spans_continuation_line(self):
        """10 課練習Ｂ-3：『例：テーブルの 上・何          テーブルの
        上に 何が ありますか。→』——箭頭印在『cue』與『示範問句』兩個
        fragment 之後，不是兩者之間；示範問句本身又是靠下一行『……か
        ばんが あります。』接續的真正答案。原本的 bug：`partition`
        依箭頭的字串位置切，把『テーブルの 上・何』跟『テーブルの
        上に 何が ありますか。』兩段全部併入 cue，answer 只剩空字
        串。正確行為：cue 只有 fragment 邊界上真正的第一段
        （『テーブルの 上・何』），示範問句與續行答案都屬於 answer。"""
        lines = group_lines(extract_fragments(PDFDoc.from_path("10.pdf")))
        sections = {s.name: s for s in split_sections(lines)}
        drills = parse_drills(sections["練習Ｂ"], 10)
        d = [x for x in drills if x["id"] == "L10-B3"][0]
        self.assertEqual(d["model_cue"], "テーブルの 上・何")
        self.assertIn("テーブルの 上に 何が ありますか。", d["model_answer"])
        self.assertIn("かばんが あります。", d["model_answer"])


class TestQuestionVariantMultiSlot(unittest.TestCase):
    """複審發現：`_reconstruct_question` 假設疑問詞只取代單一槽位，10
    課練習Ａ-5 是「どこ」整體取代兩個相鄰槽位（S=えきの／T=ちかく，
    合成「車站附近」一個複合片語）合成的案例，原本的 bug 會把 T 槽的
    基底值『ちかく』照抄進來，重建出『本屋はどこちかくにありますか。』
    這種文法錯誤的殘句。"""

    @classmethod
    def setUpClass(cls):
        lines = group_lines(extract_fragments(PDFDoc.from_path("10.pdf")))
        sections = {s.name: s for s in split_sections(lines)}
        cls.tables = parse_pattern_tables(sections["練習Ａ"], 10)

    def test_l10_a5_two_slots_collapse_into_single_question_word(self):
        t = [x for x in self.tables if x["id"] == "L10-A5"][0]
        self.assertEqual(len(t["slots"]), 2, "應偵測到兩個槽位（S=えきの、T=ちかく）")
        self.assertEqual(t["question_variant"], "本屋はどこにありますか。")
        self.assertNotIn("ちかく", t["question_variant"],
                          "T 槽的基底值不該滲入疑問句重建結果")


class TestPatternTableNoiseCharacters(unittest.TestCase):
    """延伸複審過程中額外發現的兩類「練習Ａ 雜訊字元／示範答案列污染
    槽位候選詞」問題（不在複審原始 8 筆清單裡，是自行擴大檢查角度後
    找到的）：

    - 08 課練習Ａ-2「にぎやか です にぎやか じゃ ありません」這一
      列，第二個「にぎやか」真實 x 落後參照欄位 13.8pt（比 03 課
      「13,000えん」的 6.6pt 還大），超過 `_COLUMN_TOLERANCE`，用區間
      比對會誤併回前一欄，候選詞變成「です にぎやか」。
    - 12 課練習Ａ-5「…… サッカー の ほうが おもしろいです。」＋後
      續「ほん」「しごと」是課本的示範答案區塊（用課本自己的頁面算
      繪核對過，這個區塊有自己的網底框，跟真正的槽位候選詞框是分開
      的），第一版只排除了第一行，後面兩行「ほん」「しごと」被誤判
      成真正的候選詞，混進 `slots["S"]`。
    """

    def test_l08_a2_positional_mapping_avoids_column_drift(self):
        """08 課練習Ａ-2：segment 數跟基底句欄位數相等時，依位置對應，
        不受 x 抖動影響。"""
        lines = group_lines(extract_fragments(PDFDoc.from_path("08.pdf")))
        sections = {s.name: s for s in split_sections(lines)}
        tables = parse_pattern_tables(sections["練習Ａ"], 8)
        t = [x for x in tables if x["id"] == "L08-A2"][0]
        all_values = [v for vals in t["slots"].values() for v in vals]
        self.assertNotIn("です にぎやか", all_values,
                         "「にぎやか」欄位漂移的回歸：不該把「です」跟下一欄的"
                         "「にぎやか」混成一個候選詞")
        self.assertIn("にぎやか", t["slots"]["S"])

    def test_l12_a5_sample_answer_block_excluded_from_slots(self):
        """12 課練習Ａ-5：示範答案區塊（含跨行延續）整段不計入槽位候
        選詞。"""
        lines = group_lines(extract_fragments(PDFDoc.from_path("12.pdf")))
        sections = {s.name: s for s in split_sections(lines)}
        tables = parse_pattern_tables(sections["練習Ａ"], 12)
        t = [x for x in tables if x["id"] == "L12-A5"][0]
        self.assertEqual(t["slots"]["S"], ["サッカー", "ほん", "しごと"])
        self.assertEqual(t["slots"]["T"], ["やきゅう", "えいが", "べんきょう"])
        self.assertEqual(t["rows"], [[0, 0], [1, 1], [2, 2]])


if __name__ == "__main__":
    unittest.main()
