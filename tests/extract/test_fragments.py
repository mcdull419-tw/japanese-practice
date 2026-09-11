import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments, page_fragments


class TestFragments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frags = extract_fragments(PDFDoc.from_path("07.pdf"))

    def test_has_kotoba_heading(self):
        heads = [f for f in self.frags if f.text.strip() == "ことば"]
        self.assertTrue(heads, "找不到『ことば』標題")

    def test_first_vocab_entry_present(self):
        texts = "".join(f.text for f in self.frags if f.page == 1)
        for expected in ("きります", "切ります", "剪"):
            self.assertIn(expected, texts)

    def test_fragments_carry_coordinates(self):
        for f in self.frags[:50]:
            self.assertIsInstance(f.x, float)
            self.assertIsInstance(f.y, float)
            self.assertGreater(f.size, 0.0)

    def test_ruby_fragments_are_smaller(self):
        """振假名為 4.8pt 小字；正文為 10pt 以上。兩種字級必須都存在。"""
        sizes = {round(f.size, 1) for f in self.frags}
        self.assertTrue(any(s <= 6.0 for s in sizes), "找不到小字級（振假名）")
        self.assertTrue(any(s >= 10.0 for s in sizes), "找不到正文字級")

    def test_no_misdecoding_fingerprint(self):
        """Shift-JIS 被誤讀為 GB18030 會產生這些罕見漢字。"""
        text = "".join(f.text for f in self.frags)
        for bad in "偁偄偆偊偍偐偑偒偓偔偕偖偗偘偙偠偡偣偤偦偨偩偪偭偮偯偰偱偲偵偼":
            self.assertNotIn(bad, text, "偵測到誤解碼指紋：%s" % bad)


class _MockPage:
    """Synthetic Page for pinning Td/TD coordinate arithmetic in isolation."""

    def __init__(self, number, content, resources):
        self.number = number
        self.content = content
        self.resources = resources


class _MockPDFDoc:
    """Synthetic PDFDoc backing _MockPage's /Font resource lookup."""

    def __init__(self, objects):
        self._objects = objects

    def get_object(self, num):
        return self._objects.get(num, b"")


class TestFragmentCoordinates(unittest.TestCase):
    """回歸測試：鎖定 Td/TD 位移的座標數值，不只檢查子字串是否存在。

    這兩個測試專門防範兩種「五個原始測試完全抓不到」的退化：
    (a) Td/TD 分支未觸發（例如誤用 `m.lastgroup` 導致 dispatch 失效）；
    (b) Td/TD 位移未依 PDF 規格乘上文字矩陣縮放（`x += tx` 而非
        `x += tx * self.a`）。
    兩種退化都會讓 fragment 疊在同一座標，但文字子字串序列不變，
    `test_first_vocab_entry_present` 那類測試因此無感。
    """

    def test_td_scales_by_text_matrix(self):
        """人工構造的最小內容流：BT → Tm → Td → 兩個 Tj → ET。

        數字直接取自 07.pdf 第 3 頁的實測運算子（13.2pt 字級、
        tx=-4.1818 的 TD）：依規格縮放後應落在 x=12.0（該頁其他 Tm
        反覆設定的左邊界），不縮放則會是任意數字 67.2-4.1818≈63.02。
        """
        content = (
            b"BT\n"
            b"/TT2 1 Tf\n"
            b"13.2 0 0 13.2 67.2 829.46 Tm\n"
            b"<82b1>Tj\n"
            b"-4.1818 0 TD\n"
            b"<82c6>Tj\n"
            b"ET\n"
        )
        resources = b"<< /Font << /TT2 1 0 R >> >>"
        objects = {1: b"<< /Type /Font /BaseFont /MSGothic >>"}
        page = _MockPage(number=1, content=content, resources=resources)
        doc = _MockPDFDoc(objects)

        frags = page_fragments(doc, page)

        self.assertEqual(len(frags), 2)
        self.assertAlmostEqual(frags[0].x, 67.2, places=2)
        self.assertAlmostEqual(frags[0].y, 829.46, places=2)
        self.assertAlmostEqual(frags[1].x, 12.0, places=2)
        self.assertAlmostEqual(frags[1].y, 829.46, places=2)

    def test_lesson07_vocab_row_columns_align(self):
        """實測 07.pdf 第 1 頁第一個單字列：假名／漢字／中文三欄的 x 座標。

        三個欄位同列（y 相同），x 座標彼此分開且與實測值吻合——這是
        「欄位切分」模組唯一能依賴的不變量。若座標退化成疊在同一點，
        這裡會直接爆炸。

        數值更新記錄：此列曾用 (53.4, 166.2, 497.4) 當作期望值，那是在
        `_emit_tj_array` 尚未讓 TJ 陣列內字串顯示後前進自然字寬（見
        task-3-report.md「二次修正」）、且 Tm/Tlm 尚未正確分離時量到的
        座標——兩者都是本輪修正的臭蟲，換句話說舊期望值本身就是臭蟲的
        產物。修正後重新實測，三欄座標變成 (53.4, 219.0, 384.6)，而且
        欄距幾乎相等（165.6、165.6），比舊數值（間距 112.8、331.2）更
        符合一份排版整齊的單字表該有的樣子，因此以新值為準。
        """
        frags = extract_fragments(PDFDoc.from_path("07.pdf"))
        by_text = {
            f.text.strip(): f
            for f in frags
            if f.page == 1 and f.text.strip() in ("きります", "切ります", "剪，切")
        }
        self.assertIn("きります", by_text)
        self.assertIn("切ります", by_text)
        self.assertIn("剪，切", by_text)

        kana = by_text["きります"]
        kanji_verb = by_text["切ります"]
        chinese_gloss = by_text["剪，切"]

        self.assertAlmostEqual(kana.x, 53.4, places=1)
        self.assertAlmostEqual(kanji_verb.x, 219.0, places=1)
        self.assertAlmostEqual(chinese_gloss.x, 384.6, places=1)

        # 同一列，y 應相同（在浮點誤差範圍內）。
        self.assertAlmostEqual(kana.y, 768.26, places=1)
        self.assertAlmostEqual(kanji_verb.y, kana.y, places=6)
        self.assertAlmostEqual(chinese_gloss.y, kana.y, places=6)


class TestFragmentPageBounds(unittest.TestCase):
    """回歸測試：鎖定「座標必須落在頁面範圍內」這個最粗但最有力的不變量。

    修正前，`_emit_tj_array` 只實作了 TJ 語意的一半——套用字距調整數字，
    卻沒有讓字串顯示後前進其自然字寬——導致同一個 TJ 陣列裡的中文釋義
    彼此疊在錯誤的 x，嚴重時甚至算到頁面外（例如本測試模組
    `test_lesson07_entry9_chinese_gloss_char_order` 的「打電話」曾被
    算到 x≈1020，超出頁寬 595 甚多）。深入追查後發現這其實是兩個臭蟲
    疊加：(1) TJ 陣列缺自然前進寬度、(2) 文字矩陣 Tm 與文字行矩陣 Tlm
    被誤合併成同一個 x，使 TJ 顯示文字造成的畫筆漂移污染了後續 Td/TD
    的位移基準；另外還有一個較小的第三個臭蟲：忽略 `Tc`（字元間距）
    使少數刻意疊字的裝飾文字算出負值 x。三者都修好後，1~15 課的座標
    才會全數落在頁面範圍內。

    這裡直接斷言 x 落在 `[0, 595]`（07.pdf 等全書 MediaBox 皆為
    `0 0 595 842`）——比起檢查特定子字串是否存在，這個不變量能一次
    鎖住整類「座標暴衝到頁面外」的臭蟲，不需要為每個受影響的單字各寫
    一個測試。
    """

    _PAGE_WIDTH = 595.0

    def test_lesson07_entry9_chinese_gloss_char_order(self):
        """07.pdf 第 1 頁第 9 筆單字：中文釋義「打電話」字序必須正確。

        修正前算出 打電@x≈1020、話@x≈1033（頁面外），依 x 排序後順序
        顛倒成「話打電」。修正後兩者都落在頁內，依 x 排序應正確還原成
        「打」「電」「話」三字依序出現。
        """
        frags = extract_fragments(PDFDoc.from_path("07.pdf"))
        row = [f for f in frags if f.page == 1 and abs(f.y - 605.06) < 0.5]
        self.assertTrue(row, "找不到第 9 筆單字所在列（y≈605.06）")

        chinese = [f for f in row if f.font == "TT4"]
        chinese.sort(key=lambda f: f.x)
        text = "".join(f.text for f in chinese)
        self.assertIn("打電話", text)

        for f in chinese:
            self.assertGreaterEqual(f.x, 0.0)
            self.assertLessEqual(f.x, self._PAGE_WIDTH)

    def test_no_fragment_x_outside_page_bounds(self):
        """1~15 課：沒有任何 fragment 的 x 落在 `[0, 595]` 之外。

        文字畫在頁面外是不可能真實渲染出來的——這是座標算錯的確證，
        不是版面本身特殊。這個不變量涵蓋全書，不只 07.pdf。
        """
        offenders = []
        for n in range(1, 16):
            doc = PDFDoc.from_path("%02d.pdf" % n)
            for f in extract_fragments(doc):
                if f.x < 0.0 or f.x > self._PAGE_WIDTH:
                    offenders.append((n, f.page, round(f.x, 1), f.text))
        self.assertEqual(
            offenders, [],
            "有 fragment 的 x 落在頁面外（課號, 頁碼, x, 文字）：%r" % (offenders[:10],)
        )


if __name__ == "__main__":
    unittest.main()
