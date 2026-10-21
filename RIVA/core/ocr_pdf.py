
"""RIVA OCR PDF izvjesca - javni i interni prikaz."""

from collections import Counter
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics.shapes import Drawing, Circle, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)

from core.ocr_reports import get_ocr_report

NAVY = colors.HexColor("#14263D")
TEAL = colors.HexColor("#159B98")
BLUE = colors.HexColor("#5B8DEF")
PINK = colors.HexColor("#E87991")
PURPLE = colors.HexColor("#A78BFA")
PALE = colors.HexColor("#EDF3F7")
INK = colors.HexColor("#26394D")
MUTED = colors.HexColor("#718398")
WHITE = colors.white


def _font():
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            if "RivaOCR" not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont("RivaOCR", str(path)))
            return "RivaOCR"
    raise RuntimeError("Unicode font nije pronadjen.")


def _date(value):
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        ).strftime("%d.%m.%Y. %H:%M:%S")
    except (TypeError, ValueError):
        return str(value)


def export_ocr_pdf(path, username, session_id, internal=False):
    from core.sessions import get_session

    # Svaki izvoz ponovno provjerava ovlasti.
    rows = get_ocr_report(username, session_id, internal=internal)
    session = get_session(session_id)
    if not session:
        raise ValueError("Sesija nije pronadjena.")

    font = _font()
    code = session.get("session_code") or f"RIVA-{int(session_id):06d}"
    mode = "INTERNI" if internal else "JAVNI"

    styles = {
        "title": ParagraphStyle(
            "OCRTitle", fontName=font, fontSize=18,
            leading=24, textColor=NAVY, spaceAfter=8
        ),
        "body": ParagraphStyle(
            "OCRBody", fontName=font, fontSize=9,
            leading=14, textColor=INK
        ),
        "small": ParagraphStyle(
            "OCRSmall", fontName=font, fontSize=7.5,
            leading=11, textColor=INK
        ),
        "header": ParagraphStyle(
            "OCRHeader", fontName=font, fontSize=7.5,
            leading=10, textColor=WHITE
        ),
    }

    def text(value, style="small"):
        return Paragraph(
            escape(str(value if value is not None else "-")),
            styles[style]
        )

    def heading(number, title):
        return text(f"{number:02d} | {title}", "body")

    def page_header(canvas, doc):
        canvas.saveState()
        width, height = doc.pagesize
        canvas.setFillColor(NAVY)
        canvas.rect(0, height - 44, width, 44, fill=1, stroke=0)
        canvas.setFillColor(TEAL)
        canvas.setFont(font, 16)
        canvas.drawString(40, height - 29, "RIVA")
        canvas.setFillColor(WHITE)
        canvas.setFont(font, 7.5)
        canvas.drawRightString(
            width - 40, height - 27,
            "ROAD INTELLIGENCE & VISION ANALYSIS"
        )
        canvas.setFillColor(MUTED)
        canvas.setFont(font, 8)
        canvas.drawString(40, 30, f"RIVA / {code} / {mode}")
        canvas.drawRightString(
            width - 40, 30, f"Stranica {doc.page}"
        )
        canvas.restoreState()

    confirmed = sum(
        r.get("review_status") == "CONFIRMED" for r in rows
    )
    rejected = sum(
        r.get("review_status") == "REJECTED" for r in rows
    )
    pending = sum(
        r.get("review_status") == "PENDING" for r in rows
    )
    unprocessed = len(rows) - confirmed - rejected - pending

    doc = SimpleDocTemplate(
        str(path),
        pagesize=(595.28, 841.89),
        leftMargin=40, rightMargin=40,
        topMargin=78, bottomMargin=58
    )

    story = [
        text("IZVJE\u0160\u0106E O OCR ANALIZI VOZILA", "title"),
        text(f"Sesija: {code} | Na\u010din: {mode}"),
        text(
            f"Izra\u0111eno: "
            f"{datetime.now():%d.%m.%Y. %H:%M:%S}"
        ),
        Spacer(1, 22),
    ]

    # Cetiri statisticke kartice.
    metrics = [
        ("UKUPNO PROLAZAKA", len(rows), TEAL),
        ("POTVR\u0110ENO", confirmed, BLUE),
        ("ODBIJENO", rejected, PINK),
        ("NA PROVJERI", pending, PURPLE),
    ]
    cards = Table(
        [
            [text(label) for label, _, _ in metrics],
            [text(value, "title") for _, value, _ in metrics],
        ],
        colWidths=[128] * 4,
        rowHeights=[27, 44]
    )
    card_style = [
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]
    for i, (_, _, color) in enumerate(metrics):
        card_style.append(
            ("LINEABOVE", (i, 0), (i, 0), 4, color)
        )
    cards.setStyle(TableStyle(card_style))
    story.extend([cards, Spacer(1, 23)])

    # Podaci o analizi.
    story.extend([
        heading(1, "PODACI O ANALIZI"),
        Spacer(1, 9),
    ])
    details = [
        ("Oznaka sesije", code),
        ("Korisnik", session.get("username") or "-"),
        ("Izvor", session.get("source_name") or
         session.get("source_type") or "-"),
        ("Po\u010detak obrade", _date(session.get("started_at"))),
        ("Zavr\u0161etak obrade", _date(session.get("finished_at"))),
        ("Na\u010din izvje\u0161\u0107a", mode),
    ]
    detail_table = Table(
        [[text(a), text(b)] for a, b in details],
        colWidths=[165, 347]
    )
    detail_table.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    story.extend([detail_table, Spacer(1, 22)])

    # Kru?ni grafikon OCR statusa.
    story.extend([
        heading(2, "STATUS OCR O\u010cITANJA"),
        Spacer(1, 10),
    ])

    counts = [confirmed, rejected, pending, unprocessed]
    palette = [BLUE, PINK, PURPLE, MUTED]
    labels = [
        "Potvr\u0111eno", "Odbijeno",
        "Na provjeri", "Bez OCR-a"
    ]
    total = len(rows)

    chart = Drawing(205, 145)
    if total:
        pie = Pie()
        pie.x, pie.y = 30, 8
        pie.width, pie.height = 125, 125
        pie.data = counts
        pie.startAngle = 90
        pie.direction = "clockwise"
        pie.sideLabels = False
        for i, color in enumerate(palette):
            pie.slices[i].fillColor = color
            pie.slices[i].strokeColor = WHITE
            pie.slices[i].strokeWidth = 1
        chart.add(pie)
        chart.add(Circle(
            92.5, 70.5, 36,
            fillColor=WHITE, strokeColor=WHITE
        ))
        chart.add(String(
            92.5, 74, str(total),
            fontName=font, fontSize=19,
            textAnchor="middle", fillColor=NAVY
        ))
        chart.add(String(
            92.5, 57, "OCR",
            fontName=font, fontSize=9,
            textAnchor="middle", fillColor=MUTED
        ))

    legend_data = []
    for label, count, color in zip(labels, counts, palette):
        pct = round(count * 100 / total) if total else 0
        legend_data.append([
            text(label),
            text(f"{count} ({pct}%)")
        ])

    legend = Table(legend_data, colWidths=[155, 125])
    legend.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    chart_row = Table([[chart, legend]], colWidths=[210, 302])
    chart_row.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.extend([chart_row, Spacer(1, 19)])

    # Grafikon po trakama.
    story.extend([
        heading(3, "OCR O\u010cITANJA PO TRAKAMA"),
        Spacer(1, 12),
    ])
    lane_counts = Counter(
        str(r.get("lane") or "Nepoznato") for r in rows
    )
    maximum = max(lane_counts.values(), default=1)

    if not lane_counts:
        story.append(text("Nema zabilje\u017eenih prolazaka."))
    else:
        for index, (lane, count) in enumerate(
            sorted(lane_counts.items())
        ):
            story.append(text(f"{lane}: {count}"))
            width = max(2, 470 * count / maximum)
            bar = Table(
                [["", ""]],
                colWidths=[width, 470 - width],
                rowHeights=[10]
            )
            bar.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, 0),
                 TEAL if index % 2 == 0 else BLUE),
                ("BACKGROUND", (1, 0), (1, 0), PALE),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ]))
            story.extend([Spacer(1, 5), bar, Spacer(1, 12)])

    story.extend([
        Spacer(1, 12),
        heading(4, "DETALJNA EVIDENCIJA OCR O\u010cITANJA"),
        Spacer(1, 12),
    ])

    headers = [
        "ID", "Vrijeme", "Vozilo",
        "Traka", "Registracija", "Status"
    ]
    data = [[text(h, "header") for h in headers]]

    statuses = {
        "CONFIRMED": "Potvr\u0111eno",
        "REJECTED": "Odbijeno",
        "PENDING": "Na provjeri",
    }

    for row in rows:
        data.append([
            text(row.get("id")),
            text(_date(row.get("counted_at"))),
            text(row.get("vehicle_type")),
            text(row.get("lane")),
            text(row.get("registration_text")),
            text(statuses.get(
                row.get("review_status"), "Bez OCR-a"
            )),
        ])

    table = Table(
        data,
        colWidths=[31, 103, 77, 57, 143, 101],
        repeatRows=1,
        hAlign="LEFT"
    )
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([table, Spacer(1, 18)])

    if internal:
        note = (
            "POVJERLJIVO: Izvje\u0161\u0107e sadr\u017ei "
            "stvarne registarske oznake. "
            "Namijenjeno je ovla\u0161tenim korisnicima."
        )
    else:
        note = (
            "JAVNO IZVJE\u0160\u0106E: Registarske oznake "
            "prikazane su pseudonimima. "
            "Pseudonimizirani podaci nisu anonimni."
        )

    story.append(text(note, "body"))
    story.append(Spacer(1, 8))
    story.append(text(
        "Odbijena o\u010ditanja nisu potvr\u0111ene "
        "registarske oznake."
    ))

    doc.build(
        story,
        onFirstPage=page_header,
        onLaterPages=page_header
    )
