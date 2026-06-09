"""
pdf_generator.py
================
Module to generate premium preparation guides in PDF format using ReportLab.
Includes custom typography, headers/footers, category badges, and Q&A layouts.
"""

import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY, TA_RIGHT
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether,
)

from utils import escape_html_for_reportlab, format_answer_html

# ── Colors ──
CLR_PRIMARY      = colors.HexColor("#0D1B2A")   # Dark navy
CLR_SECONDARY    = colors.HexColor("#1B2838")   # Slate
CLR_ACCENT       = colors.HexColor("#415A77")   # Steel blue
CLR_HIGHLIGHT    = colors.HexColor("#E63946")   # Coral-red accent
CLR_GOLD         = colors.HexColor("#D4A843")   # Gold accent
CLR_LIGHT_BG     = colors.HexColor("#F1F3F5")   # Very light gray
CLR_QUESTION_BG  = colors.HexColor("#E8ECF1")   # Question card bg
CLR_ANSWER_BG    = colors.HexColor("#FFFFFF")   # White
CLR_TEXT_DARK     = colors.HexColor("#1A1A2E")   # Nearly black
CLR_TEXT_BODY     = colors.HexColor("#2C3E50")   # Body text
CLR_TEXT_MUTED    = colors.HexColor("#6C757D")   # Muted text
CLR_DIVIDER       = colors.HexColor("#CED4DA")   # Light divider

CATEGORY_COLORS = {
    "Technical":        colors.HexColor("#0F3460"),
    "Behavioral":       colors.HexColor("#E63946"),
    "Situational":      colors.HexColor("#6A0572"),
    "Company-Specific": colors.HexColor("#2B7A78"),
    "General":          colors.HexColor("#415A77"),
}

def build_styles():
    """Return custom ParagraphStyles."""
    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontName="Helvetica-Bold",
            fontSize=28,
            leading=34,
            textColor=CLR_PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            fontName="Helvetica",
            fontSize=16,
            leading=22,
            textColor=CLR_ACCENT,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            textColor=CLR_TEXT_MUTED,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=24,
            textColor=CLR_PRIMARY,
            spaceBefore=20,
            spaceAfter=10,
        ),
        "category_badge": ParagraphStyle(
            "category_badge",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
        "question_num": ParagraphStyle(
            "question_num",
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=14,
            textColor=CLR_HIGHLIGHT,
        ),
        "question_text": ParagraphStyle(
            "question_text",
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=16,
            textColor=CLR_TEXT_DARK,
            spaceAfter=4,
        ),
        "answer_label": ParagraphStyle(
            "answer_label",
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=13,
            textColor=CLR_ACCENT,
            spaceBefore=4,
        ),
        "answer_text": ParagraphStyle(
            "answer_text",
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=CLR_TEXT_BODY,
            alignment=TA_JUSTIFY,
        ),
        "key_terms_label": ParagraphStyle(
            "key_terms_label",
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=12,
            textColor=CLR_GOLD,
            spaceBefore=6,
        ),
        "key_terms_text": ParagraphStyle(
            "key_terms_text",
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=12,
            textColor=CLR_TEXT_MUTED,
        ),
        "footer_text": ParagraphStyle(
            "footer_text",
            fontName="Helvetica",
            fontSize=7,
            leading=10,
            textColor=CLR_TEXT_MUTED,
            alignment=TA_CENTER,
        ),
        "summary_text": ParagraphStyle(
            "summary_text",
            fontName="Helvetica",
            fontSize=10,
            leading=15,
            textColor=CLR_TEXT_BODY,
            alignment=TA_JUSTIFY,
            spaceBefore=4,
            spaceAfter=4,
        ),
        "toc_item": ParagraphStyle(
            "toc_item",
            fontName="Helvetica",
            fontSize=10,
            leading=18,
            textColor=CLR_TEXT_BODY,
            leftIndent=12,
        ),
    }

def _header_footer(canvas, doc, company, role, candidate_name):
    """Draw header and footer on every page (except cover)."""
    page_num = doc.page
    canvas.saveState()

    if page_num > 1:
        # Header Line
        canvas.setStrokeColor(CLR_DIVIDER)
        canvas.setLineWidth(0.5)
        canvas.line(
            doc.leftMargin,
            letter[1] - 0.55 * inch,
            letter[0] - doc.rightMargin,
            letter[1] - 0.55 * inch,
        )
        canvas.setFont("Helvetica-Bold", 8)
        canvas.setFillColor(CLR_ACCENT)
        canvas.drawString(
            doc.leftMargin,
            letter[1] - 0.48 * inch,
            f"{company}  ·  {role}  ·  Interview Preparation Guide",
        )

    # Footer
    canvas.setStrokeColor(CLR_DIVIDER)
    canvas.setLineWidth(0.5)
    canvas.line(
        doc.leftMargin,
        0.55 * inch,
        letter[0] - doc.rightMargin,
        0.55 * inch,
    )
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(CLR_TEXT_MUTED)
    canvas.drawString(
        doc.leftMargin,
        0.40 * inch,
        f"Prepared for {candidate_name}  ·  {datetime.now().strftime('%B %d, %Y')}",
    )
    canvas.drawRightString(
        letter[0] - doc.rightMargin,
        0.40 * inch,
        f"Page {page_num}",
    )

    canvas.restoreState()

def _build_cover_page(story, sty, company, role, candidate_name):
    """Append cover-page flowables to story."""
    story.append(Spacer(1, 1.6 * inch))

    # Top line decoration
    story.append(HRFlowable(
        width="60%", thickness=3, color=CLR_HIGHLIGHT,
        spaceAfter=14, spaceBefore=0, hAlign="CENTER",
    ))

    story.append(Paragraph("INTERVIEW PREPARATION GUIDE", sty["cover_meta"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph(escape_html_for_reportlab(company.upper()), sty["cover_title"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(escape_html_for_reportlab(role), sty["cover_subtitle"]))
    story.append(Spacer(1, 20))

    # Bottom line decoration
    story.append(HRFlowable(
        width="40%", thickness=1, color=CLR_ACCENT,
        spaceAfter=20, spaceBefore=0, hAlign="CENTER",
    ))

    story.append(Paragraph(
        f"Prepared for <b>{escape_html_for_reportlab(candidate_name)}</b>", sty["cover_meta"],
    ))
    story.append(Paragraph(
        datetime.now().strftime("%B %d, %Y"), sty["cover_meta"],
    ))

    story.append(Spacer(1, 1.2 * inch))

    # Disclaimer
    disclaimer = (
        "This document was auto-generated using AI-powered search and your "
        "personal resume & background details. Review each answer to ensure "
        "it accurately reflects your experience before your interview."
    )
    story.append(Paragraph(disclaimer, ParagraphStyle(
        "disclaimer",
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=12,
        textColor=CLR_TEXT_MUTED,
        alignment=TA_CENTER,
    )))

    story.append(PageBreak())

def _build_summary_page(story, sty, company, role, qa_pairs):
    """Append overview summary and questions at a glance."""
    story.append(Paragraph("📋 &nbsp;Overview", sty["section_header"]))
    story.append(HRFlowable(
        width="100%", thickness=1, color=CLR_DIVIDER,
        spaceAfter=12, spaceBefore=0,
    ))

    counts = {}
    for qa in qa_pairs:
        cat = qa.get("category", "General")
        counts[cat] = counts.get(cat, 0) + 1

    summary_lines = [
        f"This guide contains <b>{len(qa_pairs)}</b> interview questions "
        f"sourced for <b>{escape_html_for_reportlab(company)}</b> targeting the <b>{escape_html_for_reportlab(role)}</b> role.",
        "Each answer is tailored to your resume, projects, and professional background.",
    ]
    for line in summary_lines:
        story.append(Paragraph(line, sty["summary_text"]))

    story.append(Spacer(1, 12))

    # Category breakdown table
    table_data = [
        [Paragraph("<b>Category</b>", sty["answer_label"]),
         Paragraph("<b>Count</b>", sty["answer_label"])],
    ]
    for cat, cnt in sorted(counts.items(), key=lambda x: -x[1]):
        clr = CATEGORY_COLORS.get(cat, CLR_ACCENT)
        badge = f'<font color="{clr.hexval()}">{escape_html_for_reportlab(cat)}</font>'
        table_data.append([
            Paragraph(badge, sty["answer_text"]),
            Paragraph(str(cnt), sty["answer_text"]),
        ])

    cat_table = Table(table_data, colWidths=[3.5 * inch, 1.2 * inch])
    cat_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CLR_LIGHT_BG),
        ("GRID", (0, 0), (-1, -1), 0.4, CLR_DIVIDER),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
    ]))
    story.append(cat_table)
    story.append(Spacer(1, 16))

    # Questions at a glance
    story.append(Paragraph("📝 &nbsp;Questions at a Glance", sty["section_header"]))
    story.append(HRFlowable(
        width="100%", thickness=1, color=CLR_DIVIDER,
        spaceAfter=10, spaceBefore=0,
    ))
    for i, qa in enumerate(qa_pairs, 1):
        q_text = qa.get("question", "")
        escaped_q = escape_html_for_reportlab(q_text[:120]) + ('…' if len(q_text) > 120 else '')
        story.append(Paragraph(
            f"<b>Q{i}.</b>  {escaped_q}",
            sty["toc_item"],
        ))

    story.append(PageBreak())

def _build_qa_card(index, qa, sty):
    """Return a list of flowables representing one Q/A card."""
    elements = []
    cat = qa.get("category", "General")
    cat_color = CATEGORY_COLORS.get(cat, CLR_ACCENT)

    # Question card category badge
    badge_text = f'<font color="white">&nbsp;{escape_html_for_reportlab(cat.upper())}&nbsp;</font>'
    badge_para = Paragraph(badge_text, sty["category_badge"])

    badge_cell = Table(
        [[badge_para]],
        colWidths=[1.4 * inch],
        rowHeights=[16],
    )
    badge_cell.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), cat_color),
        ("ALIGN", (0, 0), (0, 0), "CENTER"),
        ("VALIGN", (0, 0), (0, 0), "MIDDLE"),
        ("TOPPADDING", (0, 0), (0, 0), 2),
        ("BOTTOMPADDING", (0, 0), (0, 0), 2),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))

    elements.append(badge_cell)
    elements.append(Spacer(1, 6))

    # Question text
    escaped_q = escape_html_for_reportlab(qa.get("question", ""))
    q_para = Paragraph(
        f'<font color="{CLR_HIGHLIGHT.hexval()}">Q{index}.</font>&nbsp;&nbsp;{escaped_q}',
        sty["question_text"],
    )

    q_table = Table(
        [[q_para]],
        colWidths=[6.5 * inch],
    )
    q_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), CLR_QUESTION_BG),
        ("TOPPADDING", (0, 0), (0, 0), 10),
        ("BOTTOMPADDING", (0, 0), (0, 0), 10),
        ("LEFTPADDING", (0, 0), (0, 0), 14),
        ("RIGHTPADDING", (0, 0), (0, 0), 14),
        ("ROUNDEDCORNERS", [6, 6, 6, 6]),
    ]))
    elements.append(q_table)
    elements.append(Spacer(1, 8))

    # Answer section
    elements.append(Paragraph("TAILORED ANSWER", sty["answer_label"]))
    elements.append(Spacer(1, 2))

    # Format answer text, escaping HTML and bolding STAR labels safely
    answer_html = format_answer_html(qa.get("answer", ""), CLR_ACCENT.hexval())
    a_para = Paragraph(answer_html, sty["answer_text"])

    a_table = Table(
        [[a_para]],
        colWidths=[6.5 * inch],
    )
    a_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), CLR_ANSWER_BG),
        ("BOX", (0, 0), (0, 0), 0.5, CLR_DIVIDER),
        ("TOPPADDING", (0, 0), (0, 0), 10),
        ("BOTTOMPADDING", (0, 0), (0, 0), 10),
        ("LEFTPADDING", (0, 0), (0, 0), 14),
        ("RIGHTPADDING", (0, 0), (0, 0), 14),
        ("ROUNDEDCORNERS", [4, 4, 4, 4]),
    ]))
    elements.append(a_table)

    # Key Terms
    key_terms = qa.get("key_terms", "")
    if key_terms:
        elements.append(Spacer(1, 4))
        elements.append(Paragraph("🔑 KEY TERMS", sty["key_terms_label"]))
        elements.append(Paragraph(escape_html_for_reportlab(key_terms), sty["key_terms_text"]))

    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(
        width="100%", thickness=0.3, color=CLR_DIVIDER,
        spaceAfter=4, spaceBefore=0,
    ))

    return elements

def _build_qa_section(story, sty, qa_pairs):
    """Append the Q&A section with layout cards."""
    story.append(Paragraph("💡 &nbsp;Questions &amp; Tailored Answers", sty["section_header"]))
    story.append(HRFlowable(
        width="100%", thickness=1, color=CLR_DIVIDER,
        spaceAfter=16, spaceBefore=0,
    ))

    for i, qa in enumerate(qa_pairs, 1):
        card = _build_qa_card(i, qa, sty)
        story.append(KeepTogether(card))
        story.append(Spacer(1, 14))

def generate_pdf(qa_pairs, company, role, candidate_name, output_path):
    """Build and save the prep guide PDF.
    
    Raises:
        RuntimeError: If PDF generation fails.
    """
    if not qa_pairs:
        raise ValueError("Cannot generate PDF: Q&A list is empty.")
        
    try:
        sty = build_styles()

        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.7 * inch,
            bottomMargin=0.7 * inch,
            title=f"{company} – {role} Interview Prep",
            author=candidate_name,
        )

        story = []

        # 1) Cover page
        _build_cover_page(story, sty, company, role, candidate_name)

        # 2) Summary / Overview page
        _build_summary_page(story, sty, company, role, qa_pairs)

        # 3) Main Q&A cards
        _build_qa_section(story, sty, qa_pairs)

        # Build Document
        doc.build(
            story,
            onFirstPage=lambda c, d: _header_footer(c, d, company, role, candidate_name),
            onLaterPages=lambda c, d: _header_footer(c, d, company, role, candidate_name),
        )
    except Exception as e:
        raise RuntimeError(f"ReportLab PDF construction failed: {e}")
