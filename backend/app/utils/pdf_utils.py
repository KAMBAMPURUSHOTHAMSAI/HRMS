
from datetime import date, datetime
from decimal import Decimal
from html import escape
from io import BytesIO
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    TableStyle,
)


def _display_value(value: Any) -> str:
    if value is None:
        return "-"

    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")

    if isinstance(value, date):
        return value.isoformat()

    if isinstance(value, Decimal):
        return format(value, ",.2f")

    return str(value)


def export_pdf_bytes(
    title: str,
    rows: list[dict[str, Any]],
    columns: list[tuple[str, str]],
) -> bytes:
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        rightMargin=12 * mm,
        leftMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=title,
        author="HRMS",
    )

    styles = getSampleStyleSheet()

    story = [
        Paragraph(escape(title), styles["Title"]),
        Spacer(1, 6 * mm),
    ]

    if not rows:
        story.append(
            Paragraph("No records found for the selected filters.", styles["Normal"])
        )
        document.build(story)
        return buffer.getvalue()

    headers = [
        Paragraph(escape(heading), styles["Normal"])
        for _, heading in columns
    ]

    table_data = [headers]

    for row in rows:
        cells = []

        for key, _ in columns:
            value = _display_value(row.get(key))
            cells.append(
                Paragraph(escape(value), styles["Normal"])
            )

        table_data.append(cells)

    page_width, _ = landscape(A4)
    usable_width = page_width - (24 * mm)
    column_width = usable_width / len(columns)

    table = LongTable(
        table_data,
        colWidths=[column_width] * len(columns),
        repeatRows=1,
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#172B4D")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.lightgrey),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(table)
    document.build(story)

    return buffer.getvalue()
