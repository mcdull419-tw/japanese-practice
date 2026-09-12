import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections


class TestSections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lines = group_lines(extract_fragments(PDFDoc.from_path("07.pdf")))
        cls.sections = split_sections(lines)
        cls.by_name = {}
        for s in cls.sections:
            cls.by_name.setdefault(s.name, []).append(s)

    def test_all_expected_sections_present(self):
        for name in ("ことば", "文型", "例文", "会話", "練習Ａ", "練習Ｂ", "練習Ｃ", "問題", "文法"):
            self.assertIn(name, self.by_name, "缺少區段：%s" % name)

    def test_kaiwa_appears_once(self):
        """『会話』標題在課本出現兩次：ことば 頁尾的會話用語小框，以及對話本文。
        原型把兩者都當成新區段，導致会話#1 其實是詞彙註解。"""
        self.assertEqual(len(self.by_name["会話"]), 1,
                         "会話 區段應只有一個，實得 %d 個" % len(self.by_name["会話"]))

    def test_kaiwa_contains_dialogue(self):
        """真正的対話含ホセ・サントス的對白。

        簡報原始測試碼斷言的是『佐藤』，但實測 07.pdf 全文（含 pdf 原始
        fragment 逐一搜尋）完全沒有『佐藤』兩字——這一課的会話對話者是
        ホセ・サントス／山田一郎／山田友子／マリア・サントス，跟簡報描
        述不符（同一類「引用的例子跟實際內容不符」問題，Task 5 也出現
        過四次）。這裡改斷言『ホセ・サントス』，這個名字只出現在真正的
        対話本文，不會出現在 ことば 頁尾的詞彙小框裡，一樣能驗證切到的
        是真正的会話而不是詞彙小框。"""
        text = "".join(ln.text() for ln in self.by_name["会話"][0].lines)
        self.assertIn("ホセ・サントス", text)

    def test_sections_in_order(self):
        order = [s.name for s in self.sections]
        self.assertLess(order.index("ことば"), order.index("文型"))
        self.assertLess(order.index("文型"), order.index("例文"))
        self.assertLess(order.index("練習Ａ"), order.index("練習Ｂ"))
        self.assertLess(order.index("問題"), order.index("文法"))


if __name__ == "__main__":
    unittest.main()
