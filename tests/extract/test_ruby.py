import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.ruby import pair_ruby


class TestRuby(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frags = extract_fragments(PDFDoc.from_path("07.pdf"))
        cls.lines = group_lines(cls.frags)

    def _pairs_for(self, needle):
        for ln in self.lines:
            if needle in ln.text():
                return {p.base: p.kana for p in pair_ruby(self.frags, ln)}
        self.fail("找不到含『%s』的行" % needle)

    def test_multi_syllable_kanji(self):
        """木村 → きむら。原型的 bug 是只取第一個假名，得到『きむ』。"""
        pairs = self._pairs_for("木村さんに")
        self.assertEqual(pairs.get("木村"), "きむら")

    def test_compound_kanji(self):
        """手紙 → てがみ。"""
        pairs = self._pairs_for("手紙を")
        self.assertEqual(pairs.get("手紙"), "てがみ")

    def test_single_kanji(self):
        pairs = self._pairs_for("花を")
        self.assertEqual(pairs.get("花"), "はな")

    def test_base_appears_in_line(self):
        """每個配對的 base 必須真的出現在該行文字中，且 at 位置正確。"""
        for ln in self.lines:
            text = ln.text()
            for p in pair_ruby(self.frags, ln):
                self.assertIn(p.base, text)
                self.assertEqual(text[p.at:p.at + len(p.base)], p.base)

    def test_coverage_rate(self):
        """全課振假名字符的配對率須達 98% 以上。

        分母改成「只數非空白字元」，跟原始簡報草稿的
        `len(f.text.strip())` 不同——`strip()` 只去掉頭尾空白，振假名
        fragment 常見內部空白（例如「山田一郎」讀音單一 fragment
        ' やま  だ   いち ろう'，三個內部空白純粹是排版對齊多個漢字讀
        音群組用，不是要配對的假名字元，跟 fragment 頭尾的置中留白性質
        相同）。實測 07.pdf 這類內部空白共 262 個、佔全部 strip() 後字
        元的 27.7%（113/267 個振假名 fragment 有內部空白）——這些空白
        不可能出現在任何 `RubyPair.kana`（`pair_ruby` 依規格只收非空白
        假名字元），若照抄 `len(f.text.strip())` 當分母，即使配對完全
        正確，比率上限也只有 683/945 = 72.3%，98% 門檻無法通過，不是
        演算法缺陷，是原始測試公式把排版留白誤算成待配對字元。改成只數
        非空白字元後，同一個實作量到 98.8% 配對率，跟簡報聲稱的原型配
        對率（99%）吻合。詳見 task-5-report.md。
        """
        ruby_chars = sum(sum(1 for ch in f.text if ch.strip()) for f in self.frags
                         if f.size <= 6.0 and f.text.strip())
        paired = sum(len(p.kana) for ln in self.lines for p in pair_ruby(self.frags, ln))
        self.assertGreater(ruby_chars, 300, "第 7 課應有 400 個以上振假名字符")
        self.assertGreaterEqual(paired / ruby_chars, 0.98,
                                "配對率僅 %.1f%%" % (100.0 * paired / ruby_chars))


class TestRubyRegressions(unittest.TestCase):
    """自我審查時額外發現、修掉的具體配對錯誤——每個都曾經在 07.pdf 產生
    真的錯誤（不是覆蓋率不足，是配錯），斷言具體的配對結果以鎖住修正，
    不是只斷言「有配對出東西」。詳見 task-5-report.md「自我審查發現」。
    """

    @classmethod
    def setUpClass(cls):
        cls.frags = extract_fragments(PDFDoc.from_path("07.pdf"))
        cls.lines = group_lines(cls.frags)

    def _pairs_for(self, needle):
        for ln in self.lines:
            if needle in ln.text():
                return {p.base: p.kana for p in pair_ruby(self.frags, ln)}
        self.fail("找不到含『%s』的行" % needle)

    def test_three_kanji_compound_not_truncated(self):
        """太郎君 → たろうくん（3 漢字複合詞）。

        逐字元最近點策略（第一版實作）會把「た」誤配給隔壁的「郎」（1.8pt
        比「太」的 11.4pt 近），得到 base='郎君'、kana='たろうく'——漏掉
        開頭的「太」跟結尾的「ん」，字串本身仍然像個合理結果，弱斷言（例
        如只檢查配對率）完全抓不到。改成以 fragment 錨點找起始漢字、要求
        連續 N 個漢字後修正。
        """
        pairs = self._pairs_for("太郎君と  図書館へ")
        self.assertEqual(pairs.get("太郎君"), "たろうくん")
        self.assertEqual(pairs.get("図書館"), "としょかん")

    def test_jukujikun_reading_not_split_short(self):
        """時計 → とけい、誕生日 → たんじょうび。

        這兩個是熟字訓（不可逐字元拆分的複合詞讀音）：振假名 fragment 常
        常整個讀音只有一個（或比實際漢字數更少的）不含內部空白的區段，
        原始版只依「區段數＝連續漢字數」配對會漏掉多出來的漢字，得到
        base='時'（漏掉「計」）、base='誕生'（漏掉「日」），但 kana 卻
        已經是完整讀音——字面上看不出錯，須明確斷言 base 涵蓋完整複合詞
        才抓得到。
        """
        pairs = self._pairs_for("その  時計、すてきですね")
        self.assertEqual(pairs.get("時計"), "とけい")

        pairs2 = self._pairs_for("誕生日に  父に")
        self.assertEqual(pairs2.get("誕生日"), "たんじょうび")

    def test_no_pairing_across_vocab_table_columns(self):
        """單字表同一列「日文欄＋中文欄」之間沒有分隔字元時，不可以把假
        名配對跨欄延伸過去。

        「旅行」（headword，有振假名）後面緊接著右欄解說文字重複出現的
        「旅行（～を　します：去旅行）」（無振假名）——`Line.text()` 两欄
        之間沒有分隔符，若只看「下一個字元是不是還沒配到的漢字」就往後
        併，會把右欄那個「旅行」也吃進來，得到 base='旅行旅行'。用幾何
        字距（同一個詞的相鄰漢字間距等於字級，換欄間距實測 345.6pt）擋
        住這種跨欄合併。
        """
        pairs = self._pairs_for("旅行旅行（～を")
        self.assertEqual(pairs.get("旅行"), "りょこう")
        self.assertNotIn("旅行旅行", pairs)

    def test_no_duplicate_kana_from_overlapping_threshold(self):
        """相鄰兩個漢字的假名不可以互相重複收下。

        「木村」的「む」「ら」距離「木」（先出現的那個漢字）也在
        `RUBY_X_MAX_DIST` 門檻內，若對每個漢字各自收集「所有落在門檻內
        的假名」而不是以 fragment 為單位配對，「村」會收到「きむら」、
        「木」收到「き」，合併後變成「きむらきむら」。
        """
        pairs = self._pairs_for("木村さんに")
        self.assertEqual(pairs.get("木村"), "きむら")
        self.assertNotIn("きむらきむら", pairs.values())


if __name__ == "__main__":
    unittest.main()
