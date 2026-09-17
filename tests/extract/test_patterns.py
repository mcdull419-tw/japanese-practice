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

    def test_l08_a2_is_a_conjugation_table_not_a_broken_substitution_table(self):
        """08 課練習Ａ-2 是變化對照表（きれいです／きれいじゃありません
        這種正負形態對照），不是代入表——複審第三輪判定：這張表 fixed
        列的「です にぎやか」（欄位漂移）曾經是回歸重現的症狀，但根本
        問題是這張表從一開始就不該套用代入表的 slots／template／rows
        邏輯。改成 `table_type="conjugation"`＋`forms` 後，連不規則形
        容詞「いい／よくない」（正負形態不共用字根）都要正確切成兩
        段，不能殘留任何裝飾用「→」箭頭或跟其他列黏在一起的雜訊。"""
        lines = group_lines(extract_fragments(PDFDoc.from_path("08.pdf")))
        sections = {s.name: s for s in split_sections(lines)}
        tables = parse_pattern_tables(sections["練習Ａ"], 8)
        t = [x for x in tables if x["id"] == "L08-A2"][0]
        self.assertEqual(t["table_type"], "conjugation")
        self.assertIsNone(t["template"])
        self.assertIsNone(t["slots"])
        self.assertIn(["にぎやかです", "にぎやかじゃありません"], t["forms"])
        self.assertIn(["いいです", "よくないです"], t["forms"],
                       "不規則形容詞「いい／よくない」正負形態必須正確切成兩段")
        for pair in t["forms"]:
            for form in pair:
                self.assertNotIn("→", form)

    def test_l14_a1_verb_form_pairs_are_correct_not_merged_across_verbs(self):
        """14 課練習Ａ-1（動詞ます形／て形總表）——複審第四輪指出這張
        表原本的問題比「內容有些行混雜」嚴重得多：`_CONJUGATION_
        EXCLUDED_REPEATS` 誤把「か」「の」當助詞排除（這張表裡兩者其
        實是「書きます／書いて」「飲みます／飲んで」的動詞語幹），導
        致 11 個資料列中至少 5 列被靜默整列丟棄，殘留的列則常常把兩個
        不相干動詞的形態黏在一起（例如「いき ます」跟「＊いっ てね
        ますねて」）。根本原因是這張表版面是「一列橫跨兩個動詞」（左
        半一個動詞、右半另一個動詞，並排省版面），不是「一列一組形
        態」，改用專用的 `_parse_ms_te_reference_table`（依表頭自己的
        欄位 x 座標分四欄，不依賴同一份助詞白名單）後，斷言具體的動
        詞形態配對必須正確、且沒有互相污染。"""
        lines = group_lines(extract_fragments(PDFDoc.from_path("14.pdf")))
        sections = {s.name: s for s in split_sections(lines)}
        tables = parse_pattern_tables(sections["練習Ａ"], 14)
        t = [x for x in tables if x["id"] == "L14-A1"][0]
        self.assertEqual(t["table_type"], "conjugation")
        expected_pairs = [
            ["かきます", "かいて"],       # 書きます／書いて（Ⅰ類，か 語幹）
            ["のみます", "のんで"],       # 飲みます／飲んで（Ⅰ類，の 語幹）
            ["たべます", "たべて"],       # 食べます／食べて（Ⅱ類）
            ["いきます", "＊いって"],     # 行きます／行って（Ⅰ類，不規則て形）
            ["きます", "きて"],           # 来ます／来て（Ⅲ類）
            ["します", "して"],           # します／して（Ⅲ類）
        ]
        for pair in expected_pairs:
            self.assertIn(pair, t["forms"], "找不到形態配對 %r" % pair)
        # 不該把兩個不相干動詞的形態黏在一起（回歸的具體症狀）。
        for pair in t["forms"]:
            for form in pair:
                self.assertNotIn("ますね", form, "疑似把兩個動詞的形態接在一起：%r" % pair)
                self.assertNotIn("ますおき", form, "疑似把兩個動詞的形態接在一起：%r" % pair)
        # 表頭列本身在資料列中途重印一次（裝飾用分隔提示），不該被誤
        # 認成一組真正的動詞形態。
        self.assertNotIn(["ます形", "て形"], t["forms"])

    def test_conjugation_tables_classified_across_lessons_without_false_positives(self):
        """複審第三輪發現至少 7 張表根本是變化對照表、不是代入表：
        L04-A7（ます／ません／ました／ませんでした 四態）、L06-A5
        （ます／ましょう）、L08-A2（正負形態）、L12-A2／L12-A3（過去
        式正負形態）、L13-A3（たい形正負）、L14-A1（動詞ます形／て形
        總表）。這裡驗證分類結果，並確保沒有誤判：12 課練習Ａ-5（比較
        句型「AとBとどちらが」，基底句雖然「と」重複兩次，但那是比較
        句型本身的助詞，是正常代入表）、08 課練習Ａ-3（「い」形容詞
        「いい」候選詞本身兩個字重複，但整張表其餘三列都是正常代入，
        是正常代入表）都不該被誤判成變化對照表。"""
        expected_conjugation = {
            4: ["L04-A7"],
            6: ["L06-A5"],
            8: ["L08-A2"],
            12: ["L12-A2", "L12-A3"],
            13: ["L13-A3"],
            14: ["L14-A1"],
        }
        not_conjugation = {12: ["L12-A5"], 8: ["L08-A1", "L08-A3"]}
        for lesson, ids in expected_conjugation.items():
            lines = group_lines(extract_fragments(PDFDoc.from_path("%02d.pdf" % lesson)))
            sections = {s.name: s for s in split_sections(lines)}
            tables = {t["id"]: t for t in parse_pattern_tables(sections["練習Ａ"], lesson)}
            for tid in ids:
                self.assertEqual(tables[tid]["table_type"], "conjugation",
                                 "%s 應判定為變化對照表" % tid)
        for lesson, ids in not_conjugation.items():
            lines = group_lines(extract_fragments(PDFDoc.from_path("%02d.pdf" % lesson)))
            sections = {s.name: s for s in split_sections(lines)}
            tables = {t["id"]: t for t in parse_pattern_tables(sections["練習Ａ"], lesson)}
            for tid in ids:
                self.assertEqual(tables[tid]["table_type"], "substitution",
                                 "%s 不該被誤判成變化對照表" % tid)


class TestColumnDriftRowPairingFixes(unittest.TestCase):
    """複審第三輪發現：欄位向左漂移會讓 `_column_index` 誤判進前一
    欄，接著「沿用前一列索引」的 fallback 會用上一列不相干的內容補
    缺欄，產出課本沒教、不通順的日文句子。這裡鎖定複審親自驗證過的
    具體案例，斷言代入後的句子正確，不只是斷言 `rows` 存在。"""

    def _table(self, lesson, table_id):
        lines = group_lines(extract_fragments(PDFDoc.from_path("%02d.pdf" % lesson)))
        sections = {s.name: s for s in split_sections(lines)}
        tables = {t["id"]: t for t in parse_pattern_tables(sections["練習Ａ"], lesson)}
        return tables[table_id]

    def _sentences(self, t):
        names = sorted(t["slots"])
        out = []
        for row in t["rows"]:
            vals = {n: t["slots"][n][i] for n, i in zip(names, row)}
            out.append(t["template"].format(**vals))
        return out

    def test_l13_a4_blank_slot_becomes_empty_not_previous_rows_value(self):
        """13 課練習Ａ-4「かいもの」單獨一欄，S 欄本來就沒有替代詞
        （課本頁面算繪核對：這一列 S 欄是空白網底框，「かいもの」整
        個落在 T 欄）。斷言 `slots` 的欄位內容本身正確（`T` 要拿到
        「かいもの」、`S` 這一列要是空字串），不只是斷言代入後的句子
        通順——複審第四輪點名：只看句子讀得通會漏掉「兩欄縮成一欄、
        另一欄空白但巧合讀得通」這類回歸。"""
        t = self._table(13, "L13-A4")
        names = sorted(t["slots"])
        self.assertEqual(names, ["S", "T"])
        row = t["rows"][2]  # かいもの 那一列
        vals = {n: t["slots"][n][i] for n, i in zip(names, row)}
        self.assertEqual(vals, {"S": "", "T": "かいもの"})
        sentences = self._sentences(t)
        self.assertIn("わたしはかいものに行きます。", sentences)

    def test_l15_a3_blank_slot_becomes_empty_not_previous_rows_value(self):
        """15 課練習Ａ-3「けっこんして」單獨一欄——複審第四輪用課本網
        底框顏色核對：「けっこんして」真正屬於 T 欄，S 欄該留空，不是
        `_column_index` 曾經誤判的「S 欄有值、T 欄缺值」。斷言 `slots`
        的欄位內容本身正確，不只是斷言代入後的句子通順（「わたしは
        けっこんしています」在兩種錯誤的欄位配對下都可能巧合讀得
        通）。"""
        t = self._table(15, "L15-A3")
        names = sorted(t["slots"])
        self.assertEqual(names, ["S", "T"])
        row = t["rows"][2]  # けっこんして 那一列
        vals = {n: t["slots"][n][i] for n, i in zip(names, row)}
        self.assertEqual(vals, {"S": "", "T": "けっこんして"})
        sentences = self._sentences(t)
        self.assertIn("わたしはけっこんしています", sentences)

    def test_l13_a2_two_words_split_across_two_slots_not_merged(self):
        """13 課練習Ａ-2「外国で はたらき」課本網底框核對：「外国で」
        與「はたらき」是兩個分開的欄位（S／T），不是同一欄合併的兩個
        詞——複審第四輪點名：`わたしは外国ではたらきたいです。` 這句
        話在「S=外国で　はたらき，T=空」與「S=外国で，T=はたらき」兩
        種欄位配對下代入出來的句子剛好一模一樣，只看句子看不出配對錯
        誤，必須斷言 `slots` 本身。"""
        t = self._table(13, "L13-A2")
        names = sorted(t["slots"])
        self.assertEqual(names, ["S", "T"])
        row = t["rows"][2]  # 外国で／はたらき 那一列
        vals = {n: t["slots"][n][i] for n, i in zip(names, row)}
        self.assertEqual(vals, {"S": "外国で", "T": "はたらき"})

    def test_l14_a5_two_words_split_across_two_slots_not_merged(self):
        """14 課練習Ａ-5「日本語を べんきょうして」同樣道理：「日本語
        を」是 S、「べんきょうして」是 T，不是合併成一個 S 值、T 留
        空。"""
        t = self._table(14, "L14-A5")
        names = sorted(t["slots"])
        self.assertEqual(names, ["S", "T"])
        row = t["rows"][2]  # 日本語を／べんきょうして 那一列
        vals = {n: t["slots"][n][i] for n, i in zip(names, row)}
        self.assertEqual(vals, {"S": "日本語を", "T": "べんきょうして"})

    def test_l08_a1_left_drift_does_not_merge_into_subject_slot(self):
        """08 課練習Ａ-1「おもしろい」（單一形容詞候選詞，真實 x 比參
        照欄位偏左 13.2pt）不該被誤併進主詞欄「ワット先生は」，導致
        跟前一列的「いい」黏成「おもしろいいいです。」這種病句。"""
        t = self._table(8, "L08-A1")
        self.assertEqual(len(t["slots"]), 1, "應只有一個槽位（形容詞），主詞應維持固定")
        sentences = self._sentences(t)
        self.assertIn("ワット先生はおもしろいです。", sentences)
        for s in sentences:
            self.assertNotIn("いいいです", s)

    def test_l10_a4_left_drift_keeps_particle_with_final_form(self):
        """10 課練習Ａ-4「エレベーターの まえ」（複合詞第二段落後參照
        欄位 13.8pt，超過修正前的絕對容差）不該把「まえ」跨欄跨進基
        底句原本的虛欄「に」，導致「エレベーターのまえいます。」這種
        漏掉「に」的病句。"""
        t = self._table(10, "L10-A4")
        sentences = self._sentences(t)
        self.assertIn("ミラーさんはエレベーターの まえにいます。", sentences)
        for s in sentences:
            self.assertNotIn("まえいます", s)

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
