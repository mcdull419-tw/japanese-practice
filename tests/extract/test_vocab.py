import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections
from tools.extract.vocab import parse_vocab


def _load(lesson):
    lines = group_lines(extract_fragments(PDFDoc.from_path(lesson + ".pdf")))
    section = [s for s in split_sections(lines) if s.name == "ことば"][0]
    return parse_vocab(section)


class TestVocab(unittest.TestCase):
    """07 課：任務簡報原始的 8 個測試，一字不改地保留斷言內容。schema
    後續擴充了 `group`／`supplementary` 兩個鍵，`test_entry_with_kanji`
    的期望值已相應更新（見下方），但斷言的語意（第 1 筆的 kana/kanji/
    zh/usage 分別是什麼）完全沒變。`cls.numbered` 只留編號單字（排除
    補充單字，見 `TestVocabSupplementary`），維持原本「38 筆、編號連續
    1..38」的測試語意——補充單字的 `no` 全部是 `None`，混進 `by_no`
    字典會互相覆蓋，見模組說明「補充單字」。"""

    @classmethod
    def setUpClass(cls):
        cls.vocab = _load("07")
        cls.numbered = [v for v in cls.vocab if not v["supplementary"]]
        cls.by_no = {v["no"]: v for v in cls.numbered}

    def test_count(self):
        """第 7 課實測有 38 筆編號單字。"""
        self.assertEqual(len(self.numbered), 38)

    def test_numbers_are_contiguous(self):
        self.assertEqual(sorted(self.by_no), list(range(1, 39)))

    def test_entry_with_kanji(self):
        self.assertEqual(self.by_no[1],
                         {"no": 1, "kana": "きります", "kanji": "切ります",
                          "zh": "剪，切", "usage": None, "group": None,
                          "supplementary": False})

    def test_entry_without_kanji(self):
        v = self.by_no[3]
        self.assertEqual(v["kana"], "あげます")
        self.assertIsNone(v["kanji"])
        self.assertIn("給", v["zh"])

    def test_tight_spaced_entry(self):
        """第 10 筆 て/手：這一筆現在其實是靠欄位狀態機直接切出漢字欄
        （`fragments.py` 的 Tc 逐字元拆分修正後，「て」「手」在
        `cells()` 已經是分開的 Cell，不再需要靠 `_first_ideograph` 緊
        排切點），但斷言的答案不變。`_first_ideograph` 這條路徑本身
        不是死碼，仍有大量真實案例會觸發（例如 11 課第 36 筆
        「あに」/「兄」，見 `test_first_ideograph_path_still_exercised`），
        這裡只是誠實更新這個特定範例已經改走哪條程式碼路徑。"""
        v = self.by_no[10]
        self.assertEqual(v["kana"], "て")
        self.assertEqual(v["kanji"], "手")

    def test_first_ideograph_path_still_exercised(self):
        """11 課第 36 筆「あに」/「兄」：緊排單字（`_first_ideograph`
        切點）仍在真實資料裡大量被觸發的例子——取代 07/10 作為這條程式
        碼路徑的鎖定範例（見 `test_tight_spaced_entry` 的說明）。"""
        v11 = {x["no"]: x for x in _load("11") if not x["supplementary"]}
        self.assertEqual(v11[36]["kana"], "あに")
        self.assertEqual(v11[36]["kanji"], "兄")

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
        """07 課沒有動詞分類標記，全部單字（含補充單字）的 group 都應該是 None。"""
        for v in self.vocab:
            self.assertIsNone(v["group"], "07 課有一筆不應該有 group：%r" % (v,))

    def test_entry_38_zh_not_polluted_by_kaiwa_box(self):
        """複審修正續行機制時發現的自我迴歸：第 38 筆的 zh 曾經被
        `■会話` 小框裡好幾句對話換行後的殘句（「嗎？（去別人家時
        用）」等）誤黏進去，變成一團混亂的假資料。修正後（`last_entry`
        在遇到無法辨識的內容時重設）應該只剩單字本身的中文釋義。"""
        v = self.by_no[38]
        self.assertEqual(v["zh"], "〔～〕，好棒喲！")


class TestVocabSupplementary(unittest.TestCase):
    """補充單字：`ことば` 區段裡「---以下單字請自行練習發音---」標記
    之後、沒有編號的國名／專有名詞。見模組說明「補充單字」。"""

    @classmethod
    def setUpClass(cls):
        cls.vocab = _load("01")
        cls.supplementary = [v for v in cls.vocab if v["supplementary"]]

    def test_country_names_extracted(self):
        """01 課十一個國名不可整批遺失——這是使用者需求「單字練習」的
        核心資料，先前完全沒有被解析出來。"""
        by_kana = {v["kana"]: v for v in self.supplementary if v["kana"]}
        self.assertEqual(by_kana["アメリカ"]["zh"], "美國")
        self.assertIsNone(by_kana["アメリカ"]["kanji"])
        self.assertIsNone(by_kana["アメリカ"]["no"])
        self.assertTrue(by_kana["アメリカ"]["supplementary"])
        self.assertEqual(by_kana["ブラジル"]["zh"], "巴西")

    def test_kanji_only_proper_noun_not_split(self):
        """「韓国」是漢字寫成的專有名詞、沒有另外給假名讀音——不可套用
        緊排單字切點把它硬切成兩半，應該整個放進 kanji 欄、kana 是
        None。"""
        by_kanji = {v["kanji"]: v for v in self.supplementary if v["kanji"]}
        self.assertEqual(by_kanji["韓国"]["zh"], "韓國")
        self.assertIsNone(by_kanji["韓国"]["kana"])

    def test_compound_proper_noun_with_embedded_kanji_not_split(self):
        """「IMC／パワー電気／ブラジルエアー」本身就是複合專有名詞（含
        漢字「電気」），不是「假名讀音＋漢字寫法」配對，不可被
        `_first_ideograph` 誤切成兩半。"""
        by_kanji = {v["kanji"]: v for v in self.supplementary if v["kanji"]}
        term = "IMC／パワー電気／ブラジルエアー"
        self.assertIn(term, by_kanji)
        self.assertEqual(by_kanji[term]["zh"], "IMC/動力電器/巴西空調（虛構的公司名）")

    def test_lesson_without_marker_has_no_supplementary(self):
        """02 課完全沒有「以下單字」標記，補充單字機制永遠不會開啟，
        跟修正前行為一致（不應該無中生有）。"""
        v02 = _load("02")
        self.assertEqual([v for v in v02 if v["supplementary"]], [])


class TestVocabContinuationLines(unittest.TestCase):
    """01 課：純中文續行與替代讀音／註解續行不可遺失。見模組說明
    「續行不可遺失」。"""

    @classmethod
    def setUpClass(cls):
        cls.vocab = _load("01")
        cls.by_no = {v["no"]: v for v in cls.vocab if not v["supplementary"]}

    def test_pure_zh_continuation_across_physical_lines(self):
        """第 14 筆「しゃいん」的中文釋義因為句子太長被 PDF 自動換行成
        兩個物理行（「～公司的職員（和公司的名稱一起使」/「用，如IMCの
        しゃいん）」），原型只收到前半段、句子斷在括號說明中途。"""
        v = self.by_no[14]
        self.assertEqual(v["kana"], "しゃいん")
        self.assertEqual(v["kanji"], "社員")
        self.assertEqual(v["zh"], "～公司的職員（和公司的名稱一起使用，如IMCの しゃいん）")

    def test_alt_reading_continuation_with_fullwidth_parens(self):
        """第 4 筆「あの　ひと」下方用全形圓括號（不是搭配用法的方括
        號）給敬語替代讀音＋中文說明，續行本身又換行成兩段。"""
        v = self.by_no[4]
        self.assertEqual(v["kana"], "あの ひと")
        self.assertEqual(v["kanji"], "あの 人")
        self.assertIn("他，她，那個人", v["zh"])
        self.assertIn("あの かた", v["zh"])
        self.assertIn("あの 方", v["zh"])
        self.assertIn("あのかた", v["zh"])
        self.assertIn("禮貌形", v["zh"])

    def test_second_alt_reading_continuation_example(self):
        """第 24 筆「なんさい」同一種替代讀音續行模式，交叉驗證不是只
        有第 4 筆這個孤例。"""
        v = self.by_no[24]
        self.assertEqual(v["kana"], "なんさい")
        self.assertEqual(v["kanji"], "何歳")
        self.assertIn("幾歲", v["zh"])
        self.assertIn("おいくつ", v["zh"])
        self.assertIn("禮貌形", v["zh"])


class TestVocabUsageAlignmentFix(unittest.TestCase):
    """usage 子行對齊容差過嚴（複審修正）：子行開頭的方括號造成約
    13~14pt 的抖動，原本的 3.0pt 容差會把這些子行誤判成不對齊而整行
    遺失。見模組說明「usage 子行對齊容差過嚴」。"""

    def test_lesson11_entry1_usage_preserved(self):
        v11 = {v["no"]: v for v in _load("11") if not v["supplementary"]}
        v = v11[1]
        self.assertIsNotNone(v["usage"], "第 1 筆 usage 子行遺失")
        self.assertIn("こどもが", v["usage"]["kana"])
        self.assertIn("子どもが", v["usage"]["kanji"])

    def test_lesson11_entry4_usage_preserved(self):
        v11 = {v["no"]: v for v in _load("11") if not v["supplementary"]}
        v = v11[4]
        self.assertIsNotNone(v["usage"], "第 4 筆 usage 子行遺失")
        self.assertIn("かいしゃを", v["usage"]["kana"])
        self.assertIn("会社を", v["usage"]["kanji"])

    def test_lesson13_usage_sublines_preserved(self):
        v13 = {v["no"]: v for v in _load("13") if not v["supplementary"]}
        for no, kana_kw, kanji_kw in [
            (5, "てがみを", "手紙を"),
            (6, "きっさてんに", "喫茶店に"),
            (7, "きっさてんを", "喫茶店を"),
            (11, "こうえんを", "公園を"),
        ]:
            v = v13[no]
            self.assertIsNotNone(v["usage"], "13 課第 %d 筆 usage 子行遺失" % no)
            self.assertIn(kana_kw, v["usage"]["kana"])
            self.assertIn(kanji_kw, v["usage"]["kanji"])

    def test_lesson14_entry8_usage_preserved(self):
        """協調者明確要求的案例：14 課第 8 筆 usage 不可為 None。"""
        v14 = {v["no"]: v for v in _load("14") if not v["supplementary"]}
        v = v14[8]
        self.assertIsNotNone(v["usage"], "14 課第 8 筆 usage 子行遺失")
        self.assertIn("みぎへ", v["usage"]["kana"])
        self.assertIn("右へ", v["usage"]["kanji"])

    def test_lesson14_entries_15_17_usage_preserved(self):
        v14 = {v["no"]: v for v in _load("14") if not v["supplementary"]}
        v15 = v14[15]
        self.assertIsNotNone(v15["usage"])
        self.assertIn("じゅうしょを", v15["usage"]["kana"])
        v17 = v14[17]
        self.assertIsNotNone(v17["usage"])
        self.assertIn("あめが", v17["usage"]["kana"])


class TestVocabVerbGroup(unittest.TestCase):
    """14 課開始課本用羅馬數字標註動詞分類（Ⅰ／Ⅱ／Ⅲ類），動詞變化練
    習需要這個資訊，必須抽成獨立欄位，不能留在 kana 裡當雜訊。"""

    @classmethod
    def setUpClass(cls):
        cls.vocab = _load("14")
        cls.numbered = [v for v in cls.vocab if not v["supplementary"]]
        cls.by_no = {v["no"]: v for v in cls.numbered}

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
        """全課編號單字的 kana 欄位（非 None 者）不應有前後空白殘留
        （見任務要求 2）。補充單字（`kana` 可能是 `None`）不在此列。"""
        for v in self.numbered:
            if v["kana"] is None:
                continue
            self.assertEqual(v["kana"], v["kana"].strip(),
                              "第 %s 筆 kana 有前後空白殘留：%r" % (v["no"], v["kana"]))


class TestVocabLesson15TcFix(unittest.TestCase):
    """15 課同樣受課本大 Tc 撐開動詞分類標記與中文釋義首字的根因影響
    （4 筆：#2、7、8、9），這裡鎖住其中最早發現、已算繪核對過視覺位置
    的第 2 筆。"""

    @classmethod
    def setUpClass(cls):
        cls.vocab = _load("15")
        cls.by_no = {v["no"]: v for v in cls.vocab if not v["supplementary"]}

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


class TestVocabAdditionalTcFixDisclosure(unittest.TestCase):
    """複審比對 fragments.py 的 Tc 修正前後輸出，發現另有 5 筆（跟動詞
    分類羅馬數字無關、單純因為 Tc 逐字元拆分而連帶修正）中文釋義的角
    括號位置改變（例如 '吸煙〔〕' 這種角括號在外側的錯誤排列，修正後
    變成 '吸〔煙〕'）。第一版報告聲稱「沒有發現其他遺留問題」不成
    立，這裡補上測試鎖定並在報告揭露（見 task-7-report.md）。"""

    def test_lesson06_entries_3_and_9(self):
        v06 = {v["no"]: v for v in _load("06") if not v["supplementary"]}
        self.assertEqual(v06[3]["zh"], "吸〔煙〕")
        self.assertEqual(v06[9]["zh"], "拍〔照〕，攝〔影〕")

    def test_lesson10_entry_41(self):
        v10 = {v["no"]: v for v in _load("10") if not v["supplementary"]}
        self.assertEqual(v10[41]["zh"], "～啦～〔等〕")

    def test_lesson11_entry_4(self):
        v11 = {v["no"]: v for v in _load("11") if not v["supplementary"]}
        self.assertEqual(v11[4]["zh"], "向〔公司〕請假")

    def test_lesson12_entry_14(self):
        v12 = {v["no"]: v for v in _load("12") if not v["supplementary"]}
        self.assertEqual(v12[14]["zh"], "好〔咖啡〕")


if __name__ == "__main__":
    unittest.main()
