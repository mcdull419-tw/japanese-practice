import unittest
from tools.extract.pdfobj import PDFDoc


class TestPDFDoc(unittest.TestCase):
    def test_plain_pdf_page_count(self):
        """07.pdf 是 PDF 1.3、9 頁、無壓縮物件流。"""
        doc = PDFDoc.from_path("07.pdf")
        self.assertEqual(len(doc.pages), 9)

    def test_objstm_pdf_page_count(self):
        """11.pdf 是 PDF 1.6，Page 物件全在壓縮物件流裡，明文找不到。"""
        doc = PDFDoc.from_path("11.pdf")
        self.assertEqual(len(doc.pages), 9)

    def test_mixed_pdf_page_count(self):
        """13.pdf 同時有明文物件與壓縮物件流。"""
        doc = PDFDoc.from_path("13.pdf")
        self.assertEqual(len(doc.pages), 9)

    def test_pages_have_content_and_resources(self):
        doc = PDFDoc.from_path("07.pdf")
        first = doc.pages[0]
        self.assertEqual(first.number, 1)
        self.assertIn(b"BT", first.content)
        self.assertIn(b"/Font", first.resources)

    def test_page_one_font_resource_names(self):
        """實測值：07.pdf 第 1 頁的 /Font 資源為 /TT2 /TT4 /TT5。"""
        doc = PDFDoc.from_path("07.pdf")
        res = doc.pages[0].resources
        for name in (b"/TT2", b"/TT4", b"/TT5"):
            self.assertIn(name, res)


if __name__ == "__main__":
    unittest.main()
