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
# 審查回合修正後重新量測（見 task-8-report.md 附加段落）：`会話` 每課
# 少 1（標題不再當成一句台詞輸出），`問題` 每課少 1 或 2（純答案符號
# 條目——①②③ 選擇欄／( ○ )/( × ) 是非欄——被過濾掉，見模組說明
# 「過濾一」「過濾二」）。`文型`／`例文` 完全不受影響（這兩個區段沒
# 有任何一筆是純符號或標題）。
_EXPECTED_COUNTS = {
    "01": {"文型": 4, "例文": 5, "会話": 9, "問題": 4},
    "02": {"文型": 4, "例文": 8, "会話": 14, "問題": 6},
    "03": {"文型": 2, "例文": 7, "会話": 12, "問題": 4},
    "04": {"文型": 4, "例文": 6, "会話": 12, "問題": 6},
    "05": {"文型": 3, "例文": 6, "会話": 15, "問題": 4},
    "06": {"文型": 4, "例文": 6, "会話": 12, "問題": 5},
    "07": {"文型": 3, "例文": 7, "会話": 12, "問題": 5},
    "08": {"文型": 4, "例文": 7, "会話": 15, "問題": 5},
    "09": {"文型": 3, "例文": 7, "会話": 16, "問題": 6},
    "10": {"文型": 4, "例文": 6, "会話": 14, "問題": 5},
    "11": {"文型": 2, "例文": 7, "会話": 16, "問題": 5},
    "12": {"文型": 4, "例文": 8, "会話": 14, "問題": 5},
    "13": {"文型": 3, "例文": 6, "会話": 17, "問題": 5},
    "14": {"文型": 2, "例文": 6, "会話": 14, "問題": 5},
    "15": {"文型": 2, "例文": 7, "会話": 15, "問題": 6},
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

    def test_dialogue_title_excluded_from_output(self):
        """07 課会話：標題『ごめんください』（対話篇名，不是台詞）不應
        該以任何一句的身分出現在輸出裡；第一筆應該是真正的第一句台詞。"""
        out = _load_all("07")
        jps = [s["jp"] for s in out["会話"]]
        self.assertNotIn("ごめんください", jps, "対話標題不應該被當成一句台詞輸出")
        self.assertEqual(out["会話"][0]["jp"], "ホセ・サントス  ：ごめんください。")


import re

_KANA_RE = re.compile(r"[぀-ゟ゠-ヿ]")


class TestProblemMarkerEntriesExcluded(unittest.TestCase):
    """『問題』區段裡有些條目根本不是句子，是課本的作答格子／答案符號
    （①②③ 選擇題圈選欄、( ○ )/( × ) 是非題答案列），全 15 課掃描共
    24 筆——這些條目不含任何假名（平假名／片假名），全書其餘 369 筆
    真正的句子（文型／例文／会話／問題裡有實質內容的條目）沒有一筆是
    零假名的（已用 `TestNoRealSentenceHasZeroKana` 交叉驗證，避免誤刪
    真正的句子）。"""

    def test_no_marker_only_entries_survive(self):
        for lesson_str in _EXPECTED_COUNTS:
            out = _load_all(lesson_str)
            for r in out["問題"]:
                self.assertTrue(
                    _KANA_RE.search(r["jp"]),
                    "%s 不含假名、疑似作答格子/答案符號，不應該當成句子輸出：%r" % (r["id"], r["jp"]))

    def test_lesson07_marker_entries_removed_real_ones_kept(self):
        """07 課原本 7 筆問題，其中『問題 2』（①②③選擇欄）、『問題 3』
        （( × )/( ○ ) 是非欄）是純答案符號，過濾後應剩 5 筆，且原本的
        『問題 4』（friends／貸します 代入練習，含實質日文）仍要在。"""
        out = _load_all("07")
        jps = [s["jp"] for s in out["問題"]]
        self.assertEqual(len(jps), 5)
        self.assertFalse(any(jp in ("1)①②③\n2)①②③",) for jp in jps))
        self.assertTrue(any("友達に" in jp and "貸します" in jp for jp in jps))

    def test_lesson03_and_lesson06_only_one_marker_removed(self):
        """03／06 課的『問題』沒有 ①②③ 選擇題（只有是非題答案列），
        只會篩掉 1 筆，不是 2 筆——驗證篩選是逐條目判斷內容，不是寫死
        『每課固定砍第 2、3 筆』。"""
        out03 = _load_all("03")
        out06 = _load_all("06")
        self.assertEqual(len(out03["問題"]), 4)
        self.assertEqual(len(out06["問題"]), 5)


class TestNoRealSentenceHasZeroKana(unittest.TestCase):
    """檢查角度（否證面）：反過來證明零假名過濾沒有誤刪真正的句子——對
    全 15 課『文型』『例文』『会話』（這三個區段的內容全部是真正的句
    子，不是答案符號）逐一確認，過濾前後這三個區段的句數完全不變、且
    每一筆都通過『含假名』這個條件——如果零假名過濾器真的誤傷了正常
    句子，這三個區段的句數會跟著減少。"""

    def test_bunkei_reibun_kaiwa_unaffected_by_kana_filter(self):
        for lesson_str in _EXPECTED_COUNTS:
            out = _load_all(lesson_str)
            for name in ("文型", "例文", "会話"):
                for r in out[name]:
                    self.assertTrue(
                        _KANA_RE.search(r["jp"]),
                        "%s 不含假名——如果這是真正的句子，代表零假名不是安全的判準" % r["id"])

    def test_surviving_problem_entries_have_a_wide_safety_margin(self):
        """全 15 課『問題』裡真正倖存下來的條目，假名數最低是 19（見
        task-8-report.md 附加段落的全語料庫量測）——這裡鎖住『下限遠高
        於 0』這件事本身：`>= 10` 留了將近一半的安全邊際，不是卡在剛好
        測出來的臨界值上，避免未來資料稍有變動就假警報，但仍然遠遠不
        會跟真正的答案符號（固定是 0）混淆。"""
        min_kana = None
        for lesson_str in _EXPECTED_COUNTS:
            out = _load_all(lesson_str)
            for r in out["問題"]:
                n = len(_KANA_RE.findall(r["jp"]))
                if min_kana is None or n < min_kana:
                    min_kana = n
        self.assertGreaterEqual(min_kana, 10)


class TestKaiwaTitleRemovalPrecision(unittest.TestCase):
    """檢查角度（対話標題移除的精確性）：直接呼叫內部分組函式，逐課驗
    證『標題移除』只丟掉恰好一個 Line（標題本身），不會多丟——避免
    『不小心把第一句真台詞也當成標題砍掉』這類過度修正。"""

    def test_exactly_one_line_dropped_per_lesson(self):
        from tools.extract.sections import split_sections
        from tools.extract.sentences import _split_by_punctuation, _has_dialogue_title

        for lesson_str in _EXPECTED_COUNTS:
            frags = extract_fragments(PDFDoc.from_path(lesson_str + ".pdf"))
            lines = group_lines(frags)
            sections = {s.name: s for s in split_sections(lines)}
            kaiwa_lines = sections["会話"].lines
            groups = _split_by_punctuation(kaiwa_lines)
            self.assertTrue(_has_dialogue_title(kaiwa_lines), "%s 課應該偵測到標題" % lesson_str)
            title_group = groups[0]
            dropped_lines = {id(line) for line, _lo, _hi in title_group}
            self.assertEqual(
                len(dropped_lines), 1,
                "%s 課標題應該只對應到 1 個 Line，實得 %d 個" % (lesson_str, len(dropped_lines)))
            first_nonblank = next(l for l in kaiwa_lines if l.text().strip())
            self.assertIn(id(first_nonblank), dropped_lines,
                          "%s 課被丟掉的行應該就是區段第一個非空白行" % lesson_str)


# 課本印出來的原始編號，獨立於 `tools/extract/sentences.py` 重新掃描
# （只借用「行首 N.」這個最原始的觀察，不 import `_NUM_START_RE`），
# 用來檢查 `no` 到底等於「課本編號」還是「輸出位置」——這兩者只有在
# 中間有條目被過濾掉時才會不一樣，這正是這組測試要鎖住的。
_SRC_NUM_RE = re.compile(r"^\s*(\d+)\.")


def _source_group_starts(section):
    nums = []
    for line in section.lines:
        text = line.text()
        if not text.strip():
            continue
        m = _SRC_NUM_RE.match(text)
        if m:
            nums.append(int(m.group(1)))
    return nums


class TestIdUsesSourceNumberNotOutputPosition(unittest.TestCase):
    """複審 Critical：`no`（因此 `id`）不得由輸出位置決定，否則同一句
    話會因為過濾規則的任何變動而拿到不同 id，讓 SRS 複習歷史全部失
    效。`文型`／`例文`／`問題` 有課本印出來的 `N.` 編號可用，`no` 必
    須直接沿用它；被過濾掉的條目應該留下空號，不是讓後面的條目往前
    遞補。

    否證驗證（把 `no` 改回輸出位置，這裡的具體斷言必須變紅）已用
    scratch 副本在 shell 裡實測，指令與輸出見 task-8-report.md。"""

    def test_lesson07_problem_ids_have_gap_at_filtered_entries(self):
        """07 課『問題』原本印出 1~7 共 7 題，2、3 兩題是純答案符號被
        過濾掉——`no` 必須是 1、4、5、6、7（有缺口），不是過濾後重新
        從 1 數到 5。"""
        out = _load_all("07")
        ids = [s["id"] for s in out["問題"]]
        self.assertEqual(
            ids,
            ["L07-問題-1", "L07-問題-4", "L07-問題-5", "L07-問題-6", "L07-問題-7"])

    def test_lesson03_problem_ids_have_gap_at_filtered_entry(self):
        """03 課『問題』沒有 ①②③ 選擇題，只有『問題 2』（是非題答案
        列）被過濾——`no` 必須是 1、3、4、5，不是 1、2、3、4。"""
        out = _load_all("03")
        ids = [s["id"] for s in out["問題"]]
        self.assertEqual(ids, ["L03-問題-1", "L03-問題-3", "L03-問題-4", "L03-問題-5"])

    def test_no_matches_printed_number_across_all_lessons(self):
        """通用檢查：對全 15 課的『文型』『例文』『問題』，`no` 序列必
        須是『課本原始編號』的子序列（依相對順序保留、可以有缺口，但
        不可以出現一個沒印在課本上的號碼）；且只要這個區段真的有條目
        被過濾掉（輸出筆數 < 課本印出的編號數），`no` 序列就不應該退
        化成從 1 開始的連續整數——那正是『輸出位置』的特徵，代表 no
        又被改回位置編號了。"""
        for lesson_str in _EXPECTED_COUNTS:
            frags = extract_fragments(PDFDoc.from_path(lesson_str + ".pdf"))
            lines = group_lines(frags)
            sections = {s.name: s for s in split_sections(lines)}
            for name in ("文型", "例文", "問題"):
                section = sections[name]
                src_nums = _source_group_starts(section)
                out_nums = [s["no"] for s in parse_sentences(section, frags, int(lesson_str))]
                # 子序列檢查：out_nums 必須能依序在 src_nums 裡逐一找到
                # （允許跳過中間被過濾掉的號碼，但不能倒序、不能出現課
                # 本沒印過的號碼）。
                idx = 0
                for n in out_nums:
                    while idx < len(src_nums) and src_nums[idx] != n:
                        idx += 1
                    self.assertLess(
                        idx, len(src_nums),
                        "%s課%s 的 no=%d 不是課本印出來的編號、或順序不對" % (lesson_str, name, n))
                    idx += 1
                # 沒有被過濾就不用檢查「不能是連續位置編號」——兩者本來就會重合
                if len(out_nums) < len(src_nums) and out_nums:
                    self.assertNotEqual(
                        out_nums, list(range(1, len(out_nums) + 1)),
                        "%s課%s 有條目被過濾（%d/%d），no 卻是連續的 1..N，"
                        "疑似又退回輸出位置編號" % (lesson_str, name, len(out_nums), len(src_nums)))

if __name__ == "__main__":
    unittest.main()
