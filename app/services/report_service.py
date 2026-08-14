from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
)

from app.models.document import Document


REPORT_DIR = Path("reports")
REPORT_DIR.mkdir(parents=True, exist_ok=True)


def generate_document_report(
    document: Document
) -> Path:

    report_path = REPORT_DIR / f"document-{document.id}.pdf"

    pdf = SimpleDocTemplate(
        str(report_path),
        pagesize=A4
    )

    styles = getSampleStyleSheet()

    story = []

    # Title
    story.append(
        Paragraph(
            "Document Intelligence Report",
            styles["Title"]
        )
    )

    story.append(Spacer(1, 20))

    # File info
    story.append(
        Paragraph(
            f"<b>File:</b> {escape(document.filename)}",
            styles["BodyText"]
        )
    )

    story.append(
        Paragraph(
            f"<b>Type:</b> {escape(document.file_type.upper())}",
            styles["BodyText"]
        )
    )

    story.append(Spacer(1, 20))

    # Summary
    story.append(
        Paragraph(
            "AI Summary",
            styles["Heading2"]
        )
    )

    summary = document.summary or "No summary available."

    story.append(
        Paragraph(
            escape(summary).replace("\n", "<br/>"),
            styles["BodyText"]
        )
    )

    # Spreadsheet insights
    if document.insights:

        story.append(Spacer(1, 20))

        story.append(
            Paragraph(
                "Dataset Insights",
                styles["Heading2"]
            )
        )

        story.append(
            Paragraph(
                escape(document.insights).replace("\n", "<br/>"),
                styles["BodyText"]
            )
        )

    pdf.build(story)

    return report_path