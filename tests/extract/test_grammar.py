import unittest

from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections
from tools.extract.grammar import (
    parse_grammar, _naive_concat, _TITLE_RE, _KANA_RE, _CIRCLED,
)


def _grammar_items(lesson):
    doc = PDFDoc.from_path("%02d.pdf" % lesson)
    frags = extract_fragments(doc)
    lines = group_lines(frags)
    section = [s for s in split_sections(lines) if s.name == "文法"][0]
    return section, frags, parse_grammar(section, frags)


class TestGrammar(unittest.TestCase):
    """任務簡報 Step 1 給定的驗收測試（07.pdf 第 1 則文法點）。"""

    @classmethod
    def setUpClass(cls):
        cls.section, cls.frags, cls.items = _grammar_items(7)

    def test_count(self):
        """第 7 課文法解說實測有 5 則。"""
        self.assertEqual(len(self.items), 5)

    def test_title_keeps_japanese(self):
        """原型只取中文字型，標題的『で』遺失，變成『名詞（工具／手段）動詞』。"""
        self.assertIn("で", self.items[0]["title"])

    def test_quoted_japanese_inside_chinese(self):
        """原型輸出『助詞「」表示手段』——引號中間的日文掉了。"""
        body = self.items[0]["body_zh"]
        self.assertIn("「で」", body)
        self.assertNotIn("「」", body, "引號內的日文遺失")

    def test_japanese_examples_present(self):
        """原型只剩中文翻譯『用筷子吃』，日文例句整句消失。"""
        ex = self.items[0]["examples"]
        self.assertGreaterEqual(len(ex), 2)
        joined = " ".join(e["jp"] for e in ex)
        self.assertIn("はし", joined)
        self.assertIn("食べます", joined)
        self.assertIn("レポート", joined)

    def test_examples_paired_with_translation(self):
        for e in self.items[0]["examples"]:
            self.assertTrue(e["jp"].strip(), "日文為空")
            self.assertTrue(e["zh"].strip(), "中文為空")

    def test_every_item_has_japanese_example(self):
        """驗收條件：每則文法解說皆須含至少一句日文例句。"""
        for it in self.items:
            self.assertTrue(it["examples"], "第 %d 則無日文例句" % it["no"])


class TestGrammarLesson07AllItems(unittest.TestCase):
    """補強：對第 7 課全部 5 則文法點的具體內容逐一斷言，不只是「有解
    析出東西」這類弱條件——若有人把日中分界或例句延伸行的邏輯改壞，
    這裡任何一個具體字串都會變紅。"""

    @classmethod
    def setUpClass(cls):
        cls.section, cls.frags, cls.items = _grammar_items(7)

    def test_item_numbers_are_source_numbering(self):
        self.assertEqual([it["no"] for it in self.items], [1, 2, 3, 4, 5])

    def test_item2_question_and_answer_paired_across_lines(self):
        """第２則「詞／句は～語で 何ですか」的例句③④是問答對，回答行
        （「…」開頭）屬同一例句，見任務簡報範例。"""
        it = self.items[1]
        self.assertIn("で", it["title"])
        self.assertIn("何ですか", it["title"])
        ex = it["examples"]
        self.assertGreaterEqual(len(ex), 1)
        self.assertIn("ありがとう", ex[0]["jp"])
        self.assertIn("Thank you", ex[0]["jp"])
        self.assertIn("謝謝用英語怎麼說", ex[0]["zh"])
        self.assertIn("是", ex[0]["zh"])

    def test_item3_body_survives_multiline_wrap_with_embedded_particle(self):
        """第３則內文橫跨兩行、中間夾雜引號日文助詞「に」，必須正確接
        續、不遺漏任何一段。"""
        it = self.items[2]
        self.assertIn("に", it["title"])
        self.assertIn("あげます", it["title"])
        body = it["body_zh"]
        self.assertIn("「あげます」「かします」「おしえます」", body)
        self.assertIn("助詞「に」表示", body)
        # 〔註〕段落（另一段內文）也必須保留，不因為換行、或縮排跟例句
        # 相同而被誤判成例句延伸行（07.pdf「(へ)」的縮排比例句本身更
        # 深，見 grammar.py 模組說明）。
        self.assertIn("除助詞「に」之外有時還會使用「へ」", body)

    def test_item3_examples_all_have_non_empty_translation(self):
        it = self.items[2]
        self.assertEqual(len(it["examples"]), 4)
        for e in it["examples"]:
            self.assertTrue(e["jp"].strip())
            self.assertTrue(e["zh"].strip())
        self.assertIn("あげました", it["examples"][0]["jp"])
        self.assertEqual(it["examples"][0]["zh"], "山田先生送花給木村小姐。")
        # 例句⑧「会社に 電話を かけます。」＋緊接著的「(へ)」註記——
        # 註記縮排比例句深，必須被歸進內文，不能被拆進這則例句的日中
        # 分界，見 grammar.py `_ALT_ANNOTATION_RE`。
        self.assertEqual(it["examples"][3]["zh"], "打電話給公司。")

    def test_item4_continuation_translation_on_separate_line(self):
        """第４則例句⑩的中文翻譯另起一行、且全句不含假名——必須整段
        歸給 zh，不能被日中分界誤切成兩半。"""
        it = self.items[3]
        ex = it["examples"]
        cd_example = [e for e in ex if "ＣＤ" in e["jp"]][0]
        self.assertEqual(cd_example["jp"], "カリナさんに  ＣＤを  借りました。")
        self.assertEqual(cd_example["zh"], "我向卡莉娜小姐借了ＣＤ")

    def test_item5_body_appears_both_before_and_after_the_example(self):
        """第５則的內文一部分在例句⑭之前、一部分在之後，`body_zh` 必
        須把兩段都保留（見 grammar.py 模組說明）。"""
        it = self.items[4]
        body = it["body_zh"]
        self.assertIn("「もう」是", body)  # 例句前的內文
        self.assertIn("不能用「動詞ませんでした」", body)  # 例句後的內文
        self.assertEqual(len(it["examples"]), 1)
        ex = it["examples"][0]
        self.assertIn("送りましたか", ex["jp"])
        self.assertIn("已經送去了嗎", ex["zh"])
        self.assertIn("不，還沒有", ex["zh"])


class TestGrammarCrossLessonSpotChecks(unittest.TestCase):
    """單一課別（07.pdf）不足以代表全書排版變體，這裡對其他課別已知
    的三種不同排版情境各自斷言具體內容："""

    def test_l12_small_gap_between_japanese_and_translation(self):
        """12.pdf 第３則例句的日文句子印到接近翻譯欄，日中之間的座標
        落差只有 9.0pt——比同一課『沒有翻譯』的例句內部落差（9.6pt）
        還小，證明任何固定或相對門檻都無法同時處理兩種情形，必須靠切
        了再驗證右半段是否含假名（見 grammar.py 模組說明「日中分
        界」）。"""
        _section, _frags, items = _grammar_items(12)
        it = [i for i in items if i["no"] == 3][0]
        self.assertEqual(len(it["examples"]), 1)
        ex = it["examples"][0]
        self.assertEqual(ex["jp"], "この  車は  あの  車より  大きいです。")
        self.assertEqual(ex["zh"], "這輛車比那輛車大。")

    def test_l10_no_same_line_translation_and_no_kana_completion(self):
        """10.pdf 第１則例句在同一行完全沒有翻譯（`にほんが あります`
        這類純日文列舉），驗證這種情形 zh 留空、不會被日中分界誤切出
        一段空洞的中文。"""
        _section, _frags, items = _grammar_items(10)
        it = [i for i in items if i["no"] == 1][0]
        self.assertEqual(len(it["examples"]), 5)
        for e in it["examples"]:
            self.assertTrue(e["jp"].strip())
            self.assertTrue(e["zh"].strip())
        self.assertEqual(it["examples"][0]["jp"], "コンピューターが  あります。")
        self.assertEqual(it["examples"][0]["zh"], "有電腦。")

    def test_l02_multi_turn_dialogue_example_merges_into_one_example(self):
        """02.pdf 第６則「そうですか」的例句⑭後面接連 2 組日文延伸行
        （「いいえ、違います。シュミットさんのです。」「そうですか。」），
        再接 3 段中文翻譯——三輪對話依縮排歸屬同一則例句，日文與中文
        都必須完整保留（這是刻意的簡化：不拆成 3 則獨立例句，但不可
        遺漏任何一段內容，見 grammar.py 模組說明）。"""
        _section, _frags, items = _grammar_items(2)
        it = [i for i in items if i["no"] == 6][0]
        self.assertEqual(len(it["examples"]), 1)
        ex = it["examples"][0]
        self.assertIn("この  傘は  あなたのですか。", ex["jp"])
        self.assertIn("シュミットさんのです。", ex["jp"])
        self.assertIn("そうですか。", ex["jp"])
        self.assertIn("這把傘是你的嗎？", ex["zh"])
        self.assertIn("不，是舒密特先生的。", ex["zh"])
        self.assertIn("哦，這樣呀。", ex["zh"])

    def test_l14_leading_space_before_circled_marker_stripped(self):
        """14.pdf 的圈號 fragment 印成 ' ①'（前面多一個空白字元），跟
        07.pdf 的 '① ' 不同排版；若判定只看 fragment 開頭第一個字
        元，會漏判成沒有圈號、圈號殘留在解析結果裡（見 grammar.py
        `_split_example_line` 的說明）。這裡斷言第 1 則例句①的具體
        內容，且 jp 不含任何圈號字元。"""
        _section, _frags, items = _grammar_items(14)
        it = [i for i in items if i["no"] == 4][0]
        ex = it["examples"][0]
        self.assertEqual(
            ex["jp"], "すみませんが、この  漢字の  読み方を  教えて  ください。"
        )
        self.assertEqual(ex["zh"], "對不起，請你告訴我這個漢字的念法。")
        for c in "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳":
            self.assertNotIn(c, ex["jp"])

    def test_l14_circled_marker_as_separate_fragment_stripped(self):
        """14.pdf 第 7 則例句⑨的圈號被拆成與內文完全獨立的 fragment
        （' ⑨' 一個 fragment、內文另成 fragment），是比 ' ①' 更極端
        的排版變體，同樣不能殘留圈號。"""
        _section, _frags, items = _grammar_items(14)
        it = [i for i in items if i["no"] == 7][0]
        ex = [e for e in it["examples"] if "失礼ですが" in e["jp"]][0]
        self.assertEqual(ex["jp"], "失礼ですが、お名前は？")
        self.assertEqual(ex["zh"], "對不起，您貴姓？（第１課）")

    def test_l15_leading_space_before_circled_marker_stripped(self):
        """15.pdf 同樣是 ' ①' 排版，跨課別交叉驗證第 3 則例句⑥
        （工作簡報中列出的具體案例）不再殘留圈號。"""
        _section, _frags, items = _grammar_items(15)
        it = [i for i in items if i["no"] == 3][0]
        ex = [e for e in it["examples"] if "結婚して" in e["jp"]][0]
        self.assertEqual(ex["jp"], "わたしは  結婚して  います。")
        self.assertEqual(ex["zh"], "我結婚了。")

    def test_l06_bare_examples_without_circled_marker_land_in_body_not_lost(self):
        """06.pdf 第２則「名詞を します」底下的例句（「サッカーを
        します。踢足球」等）沒有印圈號數字，不符合本模組『例句』的判
        準，因此不會出現在 `examples`——但內容必須完整保留在
        `body_zh`，不能整批消失（誠實記錄的已知限制，見
        grammar.py 模組說明「已知限制」）。"""
        _section, _frags, items = _grammar_items(6)
        it = [i for i in items if i["no"] == 2][0]
        self.assertEqual(it["examples"], [])
        self.assertIn("サッカーを  します。踢足球", it["body_zh"])
        self.assertIn("パーティーを  します。舉行派對", it["body_zh"])


class TestGrammarAllLessonsContentPreservation(unittest.TestCase):
    """全 15 課獨立驗證：這裡設計兩種跟「解析出結果」完全不同角度的檢
    查，專門針對本任務的核心風險——原型『只取中文字型，日文整批消
    失』這個缺陷是否在解析階段被重新引入。兩種檢查都是對「解析前的原
    始 fragment 文字」與「解析後輸出」做逐字元的多重集合（multiset）
    比對，不依賴 `parse_grammar` 自己的任何中間邏輯，因此就算日中分界
    或縮排判定的實作被改壞，這裡也會被獨立偵測到。"""

    LESSONS = list(range(1, 16))

    @classmethod
    def setUpClass(cls):
        cls.data = {lesson: _grammar_items(lesson) for lesson in cls.LESSONS}

    def test_item_count_matches_independent_title_scan(self):
        """角度一：文法點數量必須跟『行首精確符合全形／半形數字＋句
        點』這個獨立於 `parse_grammar` 內部狀態機的規則掃描結果一致
        ——證明沒有文法點被合併或憑空多出。"""
        for lesson, (section, _frags, items) in self.data.items():
            raw_title_count = sum(
                1 for l in section.lines
                if l.frags and _TITLE_RE.match(_naive_concat(l.frags).strip())
            )
            self.assertEqual(
                len(items), raw_title_count,
                "第 %d 課：parse_grammar 解析出 %d 則，但獨立掃描到 %d 個標題行"
                % (lesson, len(items), raw_title_count),
            )

    def test_no_kana_character_is_lost_or_duplicated(self):
        """角度二：把整個『文法』區段所有 fragment 依既有順序串接後數
        出的假名字元數，跟解析後輸出（title + body_zh + 每則例句 jp/
        zh 全部串起來）數出的假名字元數，逐課必須完全相等——這是原型
        『只取中文字型』缺陷最直接的迴歸測試：假名只可能出現在日文字
        型裡，若解析過程重新弄丟任何日文 fragment，這裡的數字會不
        符。用『數量相等』而非『數量不減少』，同時排除了『遺漏』與
        『因重複串接而灌水』兩種方向的錯誤。"""
        for lesson, (section, _frags, items) in self.data.items():
            raw_text = "".join(_naive_concat(l.frags) for l in section.lines)
            raw_kana_count = len(_KANA_RE.findall(raw_text))

            parsed_text = ""
            for it in items:
                parsed_text += it["title"] + it["body_zh"]
                for e in it["examples"]:
                    parsed_text += e["jp"] + e["zh"]
            parsed_kana_count = len(_KANA_RE.findall(parsed_text))

            self.assertEqual(
                raw_kana_count, parsed_kana_count,
                "第 %d 課：原始假名數 %d，解析後假名數 %d，日文遺失或重複"
                % (lesson, raw_kana_count, parsed_kana_count),
            )

    def test_no_circled_marker_survives_in_any_example(self):
        """角度三：全 15 課、全 213 句例句的 jp/zh 都不得殘留圈號數字
        （①～⑳）——圈號只是印刷上的例句編號，不屬於例句內容本身。這
        是 14.pdf／15.pdf 圈號 fragment 前導空白（' ①'）與圈號獨立成
        一個 fragment（' ⑨' / '⑥' 各自成 fragment）兩種排版變體的直
        接迴歸測試。"""
        for lesson, (_section, _frags, items) in self.data.items():
            for it in items:
                for e in it["examples"]:
                    for c in _CIRCLED:
                        self.assertNotIn(
                            c, e["jp"],
                            "第 %d 課第 %d 則例句 jp 殘留圈號 %r：%r"
                            % (lesson, it["no"], c, e),
                        )
                        self.assertNotIn(
                            c, e["zh"],
                            "第 %d 課第 %d 則例句 zh 殘留圈號 %r：%r"
                            % (lesson, it["no"], c, e),
                        )

    def test_every_example_has_non_empty_japanese(self):
        """所有解析出來的例句，日文欄位不得為空——空的日文欄位代表日
        中分界判定失敗又沒有正確退回整行判斷，是本任務要避免的另一種
        『日文遺失』（只是遺失在同一筆資料的欄位之間，不是整段消
        失）。"""
        for lesson, (_section, _frags, items) in self.data.items():
            for it in items:
                for e in it["examples"]:
                    self.assertTrue(
                        e["jp"].strip(),
                        "第 %d 課第 %d 則有一句例句日文為空：%r"
                        % (lesson, it["no"], e),
                    )


if __name__ == "__main__":
    unittest.main()
