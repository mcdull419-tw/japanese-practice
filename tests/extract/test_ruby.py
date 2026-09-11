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


class TestRubyReviewFixes(unittest.TestCase):
    """審查回合找出的三個系統性根因（々、字距排版人名／假名連接複合
    詞、純數字底字）以及審查過程中額外發現的兩個交互作用臭蟲（浮點誤差
    導致的平手誤判、數字底字與清單編號的交互作用）。每個都斷言具體的配
    對結果，涵蓋 04/06/11/13.pdf。詳見 task-5-report.md 附加段落的
    RED/GREEN 證據與否證驗證。
    """

    _docs = {}

    @classmethod
    def _lines_for(cls, lesson):
        if lesson not in cls._docs:
            frags = extract_fragments(PDFDoc.from_path(lesson))
            cls._docs[lesson] = (frags, group_lines(frags))
        return cls._docs[lesson]

    def _pairs_for(self, lesson, needle):
        frags, lines = self._lines_for(lesson)
        for ln in lines:
            if needle in ln.text():
                return {p.base: p.kana for p in pair_ruby(frags, ln)}
        self.fail("在 %s 找不到含『%s』的行" % (lesson, needle))

    def test_iteration_mark_gets_own_reading(self):
        """時々 → ときどき、別々 → べつべつ。

        々（U+3005 IDEOGRAPHIC ITERATION MARK）的 `unicodedata.name` 是
        `IDEOGRAPHIC ITERATION MARK`，不含 `CJK UNIFIED`/`CJK
        COMPATIBILITY`，第一版 `_is_cjk_ideograph` 因此不承認它是底
        字，「々」永遠配不到、整組振假名連前一個漢字也跟著漏配（得到
        base='時'、kana='ときどき'，四個假名全部錯配給單一個「時」字）。
        """
        pairs = self._pairs_for("06.pdf", "わたしも  時々  ここで")
        self.assertEqual(pairs.get("時々"), "ときどき")
        self.assertNotIn("時", pairs)

        pairs2 = self._pairs_for("13.pdf", "ミラー：すみません。  別々に")
        self.assertEqual(pairs2.get("別々"), "べつべつ")

    def test_digit_gets_own_reading(self):
        """7つ 的「7」→ なな。

        第一版 `_is_cjk_ideograph` 只認漢字，數字結構性不可能當底字——
        這是第 11 課（量詞、數字課）配對率偏低的主因，直接對應使用者
        must-have 需求（數字、時間、日期／量詞練習）。
        """
        pairs = self._pairs_for("11.pdf", "会議室に  テーブルが   7つ")
        self.assertEqual(pairs.get("7"), "なな")

    def test_particle_connected_compound_not_missed(self):
        """店の人 → みせひと。

        振假名 fragment `' みせ       ひと'` 涵蓋「店」「人」兩個區段，
        中間隔著正文裡本來就有、不需要振假名的助詞「の」。第一版要求
        `reading[i+k]` 逐一緊鄰、都是漢字，看到「店」後面接的是假名「の」
        就直接判定整組配不到。
        """
        pairs = self._pairs_for("13.pdf", "店の人：ご注文は")
        self.assertEqual(pairs.get("店の人"), "みせひと")

    def test_name_letter_spacing_not_merged_across_word_boundary(self):
        """對話人名字距排版（山　田、佐　藤）刻意選擇不修——這是否證測
        試，鎖住這個決定，不是遺漏。

        對話人名常用 2~4 個半形空白把姓跟名拉開純做視覺效果（山　田：），
        但這個字距慣例跟全書內文任何兩個獨立單字之間的間隔（也是雙半形
        空白，例如「今　何」「来年　結婚」）在幾何上無法區分。13.pdf
        「今　何」剛好被 PDF 原始內容流編碼成單一個振假名 fragment，若
        放行「跳過任意數量純空白」，這兩個無關的獨立詞會被錯誤合併成一
        個 RubyPair——這比「人名配不到振假名」更糟（讀音練習題型會找不
        到獨立的「今」「何」）。因此人名字距排版目前保持配不到（不是配
        錯），這裡斷言兩件事：(1) 人名確實還是配不到，(2) 兩個獨立詞
        `今`／`何` 沒有被錯誤合併。
        """
        pairs = self._pairs_for("01.pdf", "山  田：おはよう  ございます")
        self.assertNotIn("山  田", pairs)   # 記錄殘留限制，不是本次要修的目標

        pairs2 = self._pairs_for("13.pdf", "今  何が  いちばん")
        self.assertNotIn("今  何", pairs2, "今／何是兩個獨立詞，不該被合併成一個 RubyPair")

    def test_tie_break_not_swayed_by_subpixel_float_noise(self):
        """週末 → しゅうまつ，不能因為浮點誤差選到「末」當起點而截斷成
        base='末'。

        振假名 `'しゅうまつ'` 是單一未分段區段（n=1），「週」「末」離
        錨點（x=302.4）在視覺上都恰好是半個字寬，理應平手；用目前實際
        跑的演算法量兩者的距離：週=6.60000000000008、
        末=6.599999999999909，差了約 1.7e-13，是雙精度浮點連加幾十次後
        的正常捨入誤差，不具備「誰真的比較近」的意義。n=1 時任何單一候
        選都天生湊得出合法的 1 個底字（沒有「連續底字數」這道保護），
        所以這個次像素差異如果不擋，會真的讓「末」單獨中選，產生
        `base='末'、kana='しゅうまつ'`（「末」不讀 しゅうまつ，那是
        「週末」的讀音——跟「太郎君」「980円」同一類「base 被截短、
        kana 卻是完整讀音」的錯誤，13.pdf 實測案例）。

        驗收：把 `tools.extract.ruby._TIE_EPS` 設回 `0.0` 重新執行本測
        試必須變紅（`base` 會變成 `'末'`）——已手動驗證過，見
        task-5-report.md 附加段落。
        """
        pairs = self._pairs_for(
            "13.pdf", "3) （ × ）サントスさんの  家族は  週末  公園へ"
        )
        self.assertEqual(pairs.get("週末"), "しゅうまつ")
        self.assertNotIn("末", pairs)

    def test_tie_break_does_not_merge_unrelated_words_via_skip(self):
        """毎朝 → まいあさ，不能被拉去跟後面的「7時半」「英語」錯誤合
        併（跟上面的「週末」是不同機制：這裡是 n=2 的「連續底字數」驗
        證本身就會擋掉「朝」這個錯誤起點，不特別依賴 `_TIE_EPS`——即使
        把 `_TIE_EPS` 設回 0，這兩個斷言依然成立，已手動驗證過）。
        """
        pairs = self._pairs_for("06.pdf", "毎朝  7時半に  起きます")
        self.assertEqual(pairs.get("毎朝"), "まいあさ")
        self.assertEqual(pairs.get("時半"), "じはん")
        self.assertNotIn("朝  7時半", pairs)

        pairs2 = self._pairs_for("06.pdf", "毎朝  英語の  新聞を")
        self.assertEqual(pairs2.get("毎朝"), "まいあさ")
        self.assertNotIn("朝  英語", pairs2)

    def test_digit_anchor_cross_validated_against_following_kanji(self):
        """980円 的「円」→ えん，不能被前面的數字「9」偷走。

        振假名 fragment 只有一個區段「えん」，前面帶 9 個前導半形空白把
        它推到「円」正上方——這些空白的寬度剛好讓 fragment 原始錨點跟
        「9」（980 的第一位數字）的 x 座標幾乎重合（實測差約 1.1e-13pt，
        雙精度浮點捨入誤差量級），比離
        「円」的距離（19.8pt）近得多。若只用原始錨點找最近底字，會誤判
        成 base='9'、kana='えん'（宣稱數字「9」讀作 えん，這是可驗證為
        假的錯誤讀音，比「配不到」更需要避免）。
        """
        pairs = self._pairs_for("13.pdf", "980円、牛どんは  700円です")
        self.assertEqual(pairs.get("円"), "えん")
        self.assertNotIn("9", pairs)
        self.assertNotIn("7", pairs)

    def test_digit_extension_does_not_swallow_list_numbering(self):
        """例2 的「例」→ れい，不能因為熟字訓擴張機制把緊接著的題號
        「2」一起吃進 base。

        數字廣泛用於清單編號、例句題號（例1、例2……），緊接在有振假名
        的漢字後面、自己沒有振假名是常態。把數字納入底字集合之後，如果
        熟字訓擴張（本來是為了處理「時計」「誕生日」這類讀音跨漢字未分
        段的情形）跟漢字一視同仁地把數字也吃進去，會產生 base='例2'
        （宣稱「2」是「例」讀音的一部分）。
        """
        pairs = self._pairs_for("06.pdf", "例2： （ × ）ミラーさんは")
        self.assertEqual(pairs.get("例"), "れい")
        self.assertNotIn("例2", pairs)

    def test_multi_digit_date_not_truncated_to_bare_digit(self):
        """14日 → じゅうよっか、24日 → にじゅうよっか——多位數字不能被
        截斷成單一個數字配到整個複合詞的讀音。

        「14 日」（05.pdf）跟「24 日」（15.pdf）的振假名都只有一個（或
        比實際字數更少的）區段，原始錨點最近的候選是多位數字裡的第一
        位（05 課的「1」、15 課的「2」），若只配到那一位數字，會產生
        `base='1'、kana='じゅうよっ'`／`base='2'、kana='にじゅうよっ'`
        這種錯誤宣稱——「1」不讀 じゅうよっ、「24」單獨也不讀
        にじゅうよっか，那是「14日」「24日」整個複合詞的讀音，跟
        980円 的「9」偷走「円」的讀音是同一類缺陷。

        這兩個實例源文字裡數字跟「日」之間都有一個半形空白（「14 日」
        「24 日」，排版留白，不是刻意分隔），所以合併後的 base 也包含
        這個空白字元——跟「店の人」的「の」一樣，base 涵蓋連接用的字
        元，不是只有漢字/數字本身。
        """
        pairs = self._pairs_for("05.pdf", "さくら大学（ 9月 14 日 ）")
        self.assertEqual(pairs.get("14 日"), "じゅうよっか")
        self.assertNotIn("1", pairs)

        pairs2 = self._pairs_for("15.pdf", "それは  12月  24 日です")
        self.assertEqual(pairs2.get("24 日"), "にじゅうよっか")
        self.assertNotIn("24", pairs2)
        self.assertNotIn("2", pairs2)


if __name__ == "__main__":
    unittest.main()
