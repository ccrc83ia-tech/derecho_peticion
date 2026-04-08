"""DOCX exporter — converts AI-generated raw text into a branded Word document."""

import io
import re
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

from src.domain.models import Branding
from src.domain.ports.out_ports import FileExporterPort
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
OUTPUT_DIR = _PROJECT_ROOT / "generated_docs"


class DocxEngine(FileExporterPort):

    def __init__(self, output_dir: Path = OUTPUT_DIR) -> None:
        self._output_dir = output_dir
        self._output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("DocxEngine output dir: %s", self._output_dir)

    async def export(self, content: str, branding: Branding, file_name: str) -> str:
        doc = self._build_doc(content, branding.__dict__)
        file_path = self._output_dir / file_name
        doc.save(str(file_path))
        logger.info("Document saved: %s", file_path)
        return file_name

    @classmethod
    def build_bytes(cls, content: str, branding: dict) -> bytes:
        """Build a branded DOCX in memory and return raw bytes."""
        doc = cls._build_doc(content, branding)
        buf = io.BytesIO()
        doc.save(buf)
        return buf.getvalue()

    @classmethod
    def build_pdf_bytes(cls, content: str, branding: dict) -> bytes:
        """Build a branded PDF in memory and return raw bytes."""
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()
        pdf.set_margins(25, 20, 25)

        primary_rgb = cls._parse_color(branding.get("primary_color", "#000000")) or (0, 0, 0)

        # Header
        header_text = cls._sanitize_for_pdf(branding.get("header_text", "") or "")
        if header_text:
            pdf.set_font("Helvetica", "B", 14)
            pdf.set_text_color(*primary_rgb)
            pdf.cell(0, 8, header_text, align="C", new_x="LMARGIN", new_y="NEXT")

            contact_parts = [p for p in [
                branding.get("nit", ""), branding.get("address", ""),
                branding.get("phone", ""), branding.get("email", ""),
            ] if p]
            if contact_parts:
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(120, 120, 120)
                pdf.cell(0, 5, " \u00b7 ".join(contact_parts), align="C", new_x="LMARGIN", new_y="NEXT")

            pdf.set_draw_color(180, 180, 180)
            pdf.line(25, pdf.get_y() + 3, 185, pdf.get_y() + 3)
            pdf.ln(8)

        # Body
        pdf.set_text_color(0, 0, 0)
        clean = cls._strip_markdown_fences(content)
        clean = cls._sanitize_for_pdf(clean)
        for line in clean.split("\n"):
            stripped = line.strip()
            if not stripped:
                pdf.ln(4)
                continue
            cls._pdf_add_formatted_line(pdf, stripped)

        # Footer
        footer_text = cls._sanitize_for_pdf(branding.get("footer_text", "") or "")
        if footer_text:
            pdf.ln(6)
            pdf.set_draw_color(180, 180, 180)
            pdf.line(25, pdf.get_y(), 185, pdf.get_y())
            pdf.ln(4)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(120, 120, 120)
            pdf.cell(0, 5, footer_text, align="C", new_x="LMARGIN", new_y="NEXT")

        return bytes(pdf.output())

    @staticmethod
    def _pdf_add_formatted_line(pdf, text: str) -> None:
        """Parse inline markdown and write to PDF with bold/italic."""
        import re
        pattern = re.compile(r"(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*)")
        last_end = 0
        for match in pattern.finditer(text):
            if match.start() > last_end:
                pdf.set_font("Helvetica", "", 11)
                pdf.write(6, text[last_end:match.start()])
            if match.group(2):
                pdf.set_font("Helvetica", "BI", 11)
                pdf.write(6, match.group(2))
            elif match.group(3):
                pdf.set_font("Helvetica", "B", 11)
                pdf.write(6, match.group(3))
            elif match.group(4):
                pdf.set_font("Helvetica", "I", 11)
                pdf.write(6, match.group(4))
            last_end = match.end()
        if last_end < len(text):
            pdf.set_font("Helvetica", "", 11)
            pdf.write(6, text[last_end:])
        pdf.ln(6)

    @classmethod
    def _build_doc(cls, content: str, branding: dict) -> Document:
        """Core builder shared by export() and build_bytes()."""
        doc = Document()

        for section in doc.sections:
            section.top_margin = Cm(2)
            section.bottom_margin = Cm(2)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.5)

        primary_rgb = cls._parse_color(branding.get("primary_color", "#000000"))

        # ── Header ─────────────────────────────────────────────────────────
        header_text = branding.get("header_text", "")
        if header_text:
            h = doc.add_paragraph()
            h.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = h.add_run(header_text)
            run.bold = True
            run.font.size = Pt(14)
            if primary_rgb:
                run.font.color.rgb = RGBColor(*primary_rgb)

            contact_parts = [
                p for p in [
                    branding.get("nit", ""),
                    branding.get("address", ""),
                    branding.get("phone", ""),
                    branding.get("email", ""),
                ] if p
            ]
            if contact_parts:
                c = doc.add_paragraph()
                c.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cr = c.add_run(" · ".join(contact_parts))
                cr.font.size = Pt(8)
                cr.font.color.rgb = RGBColor(120, 120, 120)

            doc.add_paragraph("─" * 60)

        # ── Body — parse raw markdown from AI ──────────────────────────────
        clean = cls._strip_markdown_fences(content)
        for line in clean.split("\n"):
            stripped = line.strip()
            if not stripped:
                doc.add_paragraph("")
                continue
            para = doc.add_paragraph()
            cls._add_formatted_runs(para, stripped)

        # ── Footer ─────────────────────────────────────────────────────────
        footer_text = branding.get("footer_text", "")
        if footer_text:
            doc.add_paragraph("")
            doc.add_paragraph("─" * 60)
            f = doc.add_paragraph()
            f.alignment = WD_ALIGN_PARAGRAPH.CENTER
            fr = f.add_run(footer_text)
            fr.font.size = Pt(8)
            fr.italic = True
            fr.font.color.rgb = RGBColor(120, 120, 120)

        return doc

    @staticmethod
    def _sanitize_for_pdf(text: str) -> str:
        """Replace unicode characters unsupported by Helvetica with ASCII equivalents."""
        replacements = {
            "\u2500": "-", "\u2501": "-", "\u2502": "|", "\u2503": "|",
            "\u2550": "=", "\u2551": "|", "\u254c": "-", "\u254d": "-",
            "\u2014": "--", "\u2013": "-", "\u2012": "-", "\u2015": "-",
            "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"',
            "\u2022": "*", "\u2023": ">", "\u25cf": "*", "\u25cb": "o",
            "\u2026": "...", "\u00b7": ".", "\u2192": "->", "\u2190": "<-",
            "\u00ae": "(R)", "\u00a9": "(C)", "\u2122": "(TM)",
            "\u00b0": " grados", "\u00ba": "o", "\u00aa": "a",
        }
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        # Remove any remaining non-latin1 characters
        return text.encode("latin-1", errors="replace").decode("latin-1")

    @staticmethod
    def _strip_markdown_fences(text: str) -> str:
        """Remove ```markdown fences if AI wraps output in them."""
        text = text.strip()
        if text.startswith("```"):
            first_nl = text.find("\n")
            if first_nl != -1:
                text = text[first_nl + 1:]
        if text.endswith("```"):
            text = text[:-3].rstrip()
        return text

    @staticmethod
    def _add_formatted_runs(para, text: str) -> None:
        """Parse inline markdown (**bold**, *italic*) into DOCX runs."""
        # Pattern: **bold**, *italic*, ***bold+italic***
        pattern = re.compile(r"(\*\*\*(.+?)\*\*\*|\*\*(.+?)\*\*|\*(.+?)\*)")
        last_end = 0
        for match in pattern.finditer(text):
            # Add text before match as plain
            if match.start() > last_end:
                para.add_run(text[last_end:match.start()])

            if match.group(2):  # ***bold+italic***
                r = para.add_run(match.group(2))
                r.bold = True
                r.italic = True
            elif match.group(3):  # **bold**
                r = para.add_run(match.group(3))
                r.bold = True
            elif match.group(4):  # *italic*
                r = para.add_run(match.group(4))
                r.italic = True

            last_end = match.end()

        # Remaining text
        if last_end < len(text):
            para.add_run(text[last_end:])

    @staticmethod
    def _parse_color(hex_color: str) -> tuple[int, int, int] | None:
        try:
            h = hex_color.lstrip("#")
            return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except (ValueError, IndexError):
            return None
