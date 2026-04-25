from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image,
    PageTemplate, Frame
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4

import io
import re
import os

router = APIRouter()

PAGE_WIDTH, PAGE_HEIGHT = A4


# 🔥 BACKGROUND FUNCTION
def add_background(canvas, doc):
    canvas.saveState()

    bg_path = r"/Users/dinaal-memah/Desktop/graduation project 2/background.png"  # 👉 YOUR CANVA IMAGE

    if os.path.exists(bg_path):
        canvas.drawImage(
            bg_path,
            0,
            0,
            width=PAGE_WIDTH,
            height=PAGE_HEIGHT
        )

    canvas.restoreState()


@router.post("/download-path-pdf")
async def download_pdf(data: dict):
    buffer = io.BytesIO()

    # 🔥 DOCUMENT WITH MARGINS (IMPORTANT FOR BACKGROUND)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # 🎨 STYLES
    title_style = ParagraphStyle(
        "ManaraTitle",
        parent=styles["Title"],
        fontSize=26,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,
        spaceAfter=10
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Heading3"],
        alignment=1,
        textColor=colors.HexColor("#334155"),
        spaceAfter=20
    )

    header_style = ParagraphStyle(
        "StepTitle",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=6
    )

    course_style = ParagraphStyle(
        "Course",
        parent=styles["Normal"],
        textColor=colors.HexColor("#475569"),
        spaceAfter=6
    )

    elements = []

    # ✅ LOGO
    logo_path = r"/Users/dinaal-memah/Desktop/graduation project 2/logo.png"

    if os.path.exists(logo_path):
        logo = Image(logo_path, width=80, height=80)
        logo.hAlign = "CENTER"
        elements.append(logo)
        elements.append(Spacer(1, 10))

    # 🔥 HEADER
    target_course = (
        data.get("target_course")
        or data.get("course_name")
        or "Path"
    )

    elements.append(Paragraph("Manara", title_style))
    elements.append(
        Paragraph(f"Learning Path for <b>{target_course}</b>", subtitle_style)
    )

    # divider
    elements.append(
        Table([[""]], colWidths=[450], style=[
            ("LINEBELOW", (0, 0), (-1, -1), 2, colors.HexColor("#0f172a"))
        ])
    )
    elements.append(Spacer(1, 20))

    # 📚 PATH CONTENT
    path = data.get("learning_path", [])

    for step in path:
        elements.append(
            Paragraph(
                f"{step.get('step_number', '')}. {step.get('topic_name', '')}",
                header_style
            )
        )

        elements.append(
            Paragraph(
                f"<b>Course:</b> {step.get('source_course', '')}",
                course_style
            )
        )

        subtopics = [
            [f"• {sub.get('subtopic_name', '')}"]
            for sub in step.get("weak_subtopics", [])
        ]

        if subtopics:
            table = Table(subtopics, colWidths=[450])
            table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#e2e8f0")),
                    ("INNERPADDING", (0, 0), (-1, -1), 8),
                ])
            )
            elements.append(table)

        elements.append(Spacer(1, 16))

    # 🔥 BACKGROUND TEMPLATE
    frame = Frame(
        40, 40,
        PAGE_WIDTH - 80,
        PAGE_HEIGHT - 80,
        id='normal'
    )

    template = PageTemplate(
        id='background',
        frames=frame,
        onPage=add_background
    )

    doc.addPageTemplates([template])

    # BUILD PDF
    doc.build(elements)

    buffer.seek(0)

    # ✅ SAFE FILENAME
    safe_name = re.sub(r"[^\w\s-]", "", target_course).strip().replace(" ", "_")

    if not safe_name:
        safe_name = "Path"

    filename = f"Manara_{safe_name}_Path.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
