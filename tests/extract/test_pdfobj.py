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

    def test_kids_indirect_reference(self):
        """/Kids 的值可以是間接參照（`/Kids 9 0 R`）而非內嵌陣列。

        現有 51 份課本 PDF 都不含這種結構，用合成的最小物件表驗證，
        不觸碰任何根目錄的 *.pdf。
        """
        synthetic = b"""
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids 9 0 R /Count 2 >>
endobj
9 0 obj
[ 3 0 R 4 0 R ]
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>
endobj
4 0 obj
<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>
endobj
6 0 obj
<< /Length 17 >>
stream
BT (page3) Tj ET
endstream
endobj
7 0 obj
<< /Length 17 >>
stream
BT (page4) Tj ET
endstream
endobj
"""
        doc = PDFDoc(synthetic)
        self.assertEqual(len(doc.pages), 2)
        self.assertIn(b"BT", doc.pages[0].content)
        self.assertIn(b"/Font", doc.pages[0].resources)
        self.assertIn(b"BT", doc.pages[1].content)


if __name__ == "__main__":
    unittest.main()
