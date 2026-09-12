import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections
from tools.extract.sentences import parse_sentences


class TestSentences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frags = extract_fragments(PDFDoc.from_path("07.pdf"))
        lines = group_lines(cls.frags)
        cls.sections = {s.name: s for s in split_sections(lines)}

    def _parse(self, name):
        return parse_sentences(self.sections[name], self.frags, 7)

    def test_bunkei_count(self):
        """第 7 課文型實測為 3 句。"""
        self.assertEqual(len(self._parse("文型")), 3)

    def test_bunkei_first_sentence(self):
        s = self._parse("文型")[0]
        self.assertIn("わたしは", s["jp"])
        self.assertIn("ワープロで", s["jp"])
        self.assertIn("手紙を", s["jp"])
        self.assertIn("書きます", s["jp"])
        self.assertTrue(s["jp"].rstrip().endswith("。"))

    def test_bunkei_ruby_attached(self):
        s = self._parse("文型")[0]
        pairs = {r["base"]: r["kana"] for r in s["ruby"]}
        self.assertEqual(pairs.get("手紙"), "てがみ")

    def test_alternative_particle_captured(self):
        """文型 3 課本標註『（から）』，表示 に／から 皆可，須存進 alt。"""
        s = self._parse("文型")[2]
        self.assertIn("もらいました", s["jp"])
        self.assertIn("から", s["alt"])
        self.assertNotIn("（", s["jp"], "替代形註記不應留在句子本體")

    def test_reibun_count(self):
        """第 7 課例文實測為 7 組。"""
        self.assertEqual(len(self._parse("例文")), 7)

    def test_ids_are_unique_and_stable(self):
        ids = [s["id"] for s in self._parse("文型") + self._parse("例文")]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self._parse("文型")[0]["id"], "L07-文型-1")


def _load_all(lesson_str):
    lesson = int(lesson_str)
    frags = extract_fragments(PDFDoc.from_path(lesson_str + ".pdf"))
    lines = group_lines(frags)
    sections = {s.name: s for s in split_sections(lines)}
    out = {}
    for name in ("文型", "例文", "会話", "問題"):
        out[name] = parse_sentences(sections[name], frags, lesson)
    return out


# 全 15 課、四個區段各自的句數——用目前實際跑的 parse_sentences 重新量測
# （見 task-8-report.md），逐課鎖住，任何一課的切分邏輯壞掉都會變紅。
_EXPECTED_COUNTS = {
    "01": {"文型": 4, "例文": 5, "会話": 10, "問題": 6},
    "02": {"文型": 4, "例文": 8, "会話": 15, "問題": 8},
    "03": {"文型": 2, "例文": 7, "会話": 13, "問題": 5},
    "04": {"文型": 4, "例文": 6, "会話": 13, "問題": 8},
    "05": {"文型": 3, "例文": 6, "会話": 16, "問題": 6},
    "06": {"文型": 4, "例文": 6, "会話": 13, "問題": 6},
    "07": {"文型": 3, "例文": 7, "会話": 13, "問題": 7},
    "08": {"文型": 4, "例文": 7, "会話": 16, "問題": 7},
    "09": {"文型": 3, "例文": 7, "会話": 17, "問題": 7},
    "10": {"文型": 4, "例文": 6, "会話": 15, "問題": 7},
    "11": {"文型": 2, "例文": 7, "会話": 17, "問題": 7},
    "12": {"文型": 4, "例文": 8, "会話": 15, "問題": 6},
    "13": {"文型": 3, "例文": 6, "会話": 18, "問題": 6},
    "14": {"文型": 2, "例文": 6, "会話": 15, "問題": 7},
    "15": {"文型": 2, "例文": 7, "会話": 16, "問題": 7},
}


class TestAllLessonsCounts(unittest.TestCase):
    """檢查角度一（涵蓋率）：全 15 課、四個區段各自的句數是否符合實測
    值。這不是「數量大於 0」這種弱斷言——任何一課任何一個區段切錯（多
    切、少切、被整段吞掉）都會讓對應的那一格變紅，逐課逐區段可回溯。"""

    def test_counts_per_lesson(self):
        for lesson_str, expected in _EXPECTED_COUNTS.items():
            with self.subTest(lesson=lesson_str):
                out = _load_all(lesson_str)
                for name, n in expected.items():
                    self.assertEqual(
                        len(out[name]), n,
                        "%s課 %s 應有 %d 句，實得 %d" % (lesson_str, name, n, len(out[name])))


class TestRubyOffsetInvariant(unittest.TestCase):
    """檢查角度二（結構完整性）：對全 15 課、四個區段的每一筆輸出，逐一
    驗證 `jp[at:at+len(base)] == base`——這個不變量是任務簡報明確要求
    （見 ruby.py 模組說明「已知既有事實」），也是最容易被『多行拼接／
    裁切頭尾空白』的偏移量算術錯誤破壞的地方。任何一次偏移算錯，這裡
    都會抓到具體是哪一課哪個區段第幾句、哪一組 ruby 錯位。"""

    def test_ruby_at_matches_base_everywhere(self):
        bad = []
        for lesson_str in _EXPECTED_COUNTS:
            out = _load_all(lesson_str)
            for name, sentences in out.items():
                for s in sentences:
                    for r in s["ruby"]:
                        seg = s["jp"][r["at"]: r["at"] + len(r["base"])]
                        if seg != r["base"]:
                            bad.append((s["id"], r, seg))
        self.assertEqual(bad, [], "ruby at 偏移量跟 base 對不上：%r" % (bad,))

    def test_no_duplicate_ids_within_lesson(self):
        """檢查角度三（身分穩定性附加驗證）：同一課四個區段合起來的 id
        不可重複——這是 SRS 追蹤依賴的前提（見任務簡報）。"""
        for lesson_str in _EXPECTED_COUNTS:
            out = _load_all(lesson_str)
            ids = [s["id"] for sentences in out.values() for s in sentences]
            self.assertEqual(len(ids), len(set(ids)), "%s課 id 有重複" % lesson_str)

    def test_deterministic_across_repeated_calls(self):
        """id 不含亂數——同一課重新解析兩次必須得到逐字相同的結果。"""
        out1 = _load_all("09")
        out2 = _load_all("09")
        self.assertEqual(out1, out2)


class TestAlternativeFormAnnotation(unittest.TestCase):
    """替代形註記 alt 不是只有 07 課文型 3 這一個孤例——01 課文型 2
    『（では）』、13 課文型 3『（が）』是另外兩個獨立樣本，三課的替代詞
    各不相同，能排除『剛好命中單一硬編碼字串』的巧合。"""

    def test_lesson01_bunkei2_alt_dewa(self):
        out = _load_all("01")
        s = out["文型"][1]
        self.assertIn("学生じゃ", s["jp"])
        self.assertIn("ありません", s["jp"])
        self.assertEqual(s["alt"], ["では"])
        self.assertNotIn("（", s["jp"])

    def test_lesson13_bunkei2_alt_ga(self):
        """13 課文型 2（0-based index 1）：『てんぷらを食べたいです』
        句尾標註『（が）』，表示『を』／『が』皆可。"""
        out = _load_all("13")
        s = out["文型"][1]
        self.assertIn("食べたいです", s["jp"])
        self.assertEqual(s["alt"], ["が"])
        self.assertNotIn("（", s["jp"])

    def test_lessons_without_annotation_have_empty_alt(self):
        out = _load_all("07")
        self.assertEqual(out["文型"][0]["alt"], [])
        self.assertEqual(out["文型"][1]["alt"], [])


class TestKaiwaLineWrapAndSpeakerBoundary(unittest.TestCase):
    """会話（対話本文）沒有行首編號，切分邏輯完全不同於文型／例文／問
    題，這裡用具體課別、具體句子鎖住三種曾經在探勘時發現、必須正確處
    理的形狀（見 tools/extract/sentences.py 模組說明「対話換行與說話者
    邊界」），而不是只斷言『有解析出東西』。"""

    def test_wrapped_sentence_glued_across_print_lines(self):
        """08 課会話：『山田一郎：マリアさんは もう 日本の 生活に』印
        到一半換行，『慣れましたか。』接在下一行——必須黏成一句，不能
        斷尾也不能各自成句。"""
        out = _load_all("08")
        joined = [s["jp"] for s in out["会話"]]
        self.assertIn("山田一郎        ：マリアさんは  もう  日本の  生活に慣れましたか。", joined)

    def test_speaker_only_line_glued_to_next_line_content(self):
        """15 課会話：『木  村：』單獨一行、內容留到下一行『3人です。』
        ──必須黏成一句，說話者標籤不能孤立成一句空殼。"""
        out = _load_all("15")
        joined = [s["jp"] for s in out["会話"]]
        self.assertIn("木  村：3人です。", joined)
        self.assertNotIn("木  村：", joined, "說話者標籤不應該單獨成一句空殼")

    def test_missing_period_does_not_merge_into_next_speaker(self):
        """11 課会話：『郵便局員：500円です』這一行原書本身沒有印句
        號（已用逐 fragment 掃描確認，不是抽取遺漏，見 task-8-report.md），
        緊接著是全新說話者『ワン：どのくらい かかりますか。』──兩者絕
        對不可以被黏成一句。"""
        out = _load_all("11")
        joined = [s["jp"] for s in out["会話"]]
        self.assertIn("郵便局員：500円です", joined)
        for jp in joined:
            self.assertNotIn("500円です  ワン", jp)
            self.assertNotIn("500円ですワ", jp)

    def test_dialogue_title_is_isolated_from_first_utterance(self):
        """07 課会話：標題『ごめんください』（対話篇名，沒有句號、後面
        接空白行才是真正對話開始）不可以跟第一句台詞黏在一起。"""
        out = _load_all("07")
        first = out["会話"][0]
        self.assertEqual(first["jp"], "ごめんください")


if __name__ == "__main__":
    unittest.main()
