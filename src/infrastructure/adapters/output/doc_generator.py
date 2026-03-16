"""DOCX exporter — converts AI-generated raw text into a branded Word document."""

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
        doc = Document()

        # Page margins
        for section in doc.sections:
            section.top_margin = Cm(2)
            section.bottom_margin = Cm(2)
            section.left_margin = Cm(2.5)
            section.right_margin = Cm(2.5)

        primary_rgb = self._parse_color(branding.primary_color)

        # ── Header ─────────────────────────────────────────────────────────
        if branding.header_text:
            h = doc.add_paragraph()
            h.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = h.add_run(branding.header_text)
            run.bold = True
            run.font.size = Pt(14)
            if primary_rgb:
                run.font.color.rgb = RGBColor(*primary_rgb)

            # Contact info from branding
            contact_parts = [
                p for p in [
                    branding.nit,
                    branding.address,
                    branding.phone,
                    branding.email,
                ] if p
            ]
            if contact_parts:
                c = doc.add_paragraph()
                c.alignment = WD_ALIGN_PARAGRAPH.CENTER
                cr = c.add_run(" · ".join(contact_parts))
                cr.font.size = Pt(8)
                cr.font.color.rgb = RGBColor(120, 120, 120)

            # Separator line
            doc.add_paragraph("─" * 60)

        # ── Body — parse raw markdown from AI ──────────────────────────────
        clean = self._strip_markdown_fences(content)
        for line in clean.split("\n"):
            stripped = line.strip()
            if not stripped:
                doc.add_paragraph("")
                continue
            para = doc.add_paragraph()
            self._add_formatted_runs(para, stripped)

        # ── Footer ─────────────────────────────────────────────────────────
        if branding.footer_text:
            doc.add_paragraph("")
            doc.add_paragraph("─" * 60)
            f = doc.add_paragraph()
            f.alignment = WD_ALIGN_PARAGRAPH.CENTER
            fr = f.add_run(branding.footer_text)
            fr.font.size = Pt(8)
            fr.italic = True
            fr.font.color.rgb = RGBColor(120, 120, 120)

        file_path = self._output_dir / file_name
        doc.save(str(file_path))
        logger.info("Document saved: %s", file_path)
        return file_name

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
