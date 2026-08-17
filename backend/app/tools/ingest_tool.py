from pathlib import Path
import fitz  # PyMuPDF
from docx import Document
from backend.app.tools.base_tool import BaseTool
from backend.app.core.exceptions import FileIngestError

class IngestTool(BaseTool):
    name = "ingest"
    description = "解析上传的简历/文档文件（PDF/DOCX），提取纯文本"

    def run(self, file_path: str) -> str:
        suffix = Path(file_path).suffix.lower()
        if suffix == ".pdf":
            try:
                doc = fitz.open(file_path)
                return "\n".join(page.get_text() for page in doc)
            except Exception as e:
                raise FileIngestError(f"PDF 解析失败：{file_path}") from e
        elif suffix == ".docx":
            try:
                d = Document(file_path)
                return "\n".join(p.text for p in d.paragraphs)
            except Exception as e:
                raise FileIngestError(f"DOCX 解析失败：{file_path}") from e
        else:
            raise FileIngestError(f"不支持的文件类型：{suffix}（仅支持 PDF 和 DOCX）")
