from core.ocr_reports import get_ocr_report
"""RIVA | Moderni prometni izvjestaji i PDF izvoz bez OCR podataka."""
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QPushButton,
    QComboBox, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QFileDialog, QMessageBox, QScrollArea, QGridLayout,
    QProgressBar, QDialog,
)
from core.sessions import (
    get_recent_sessions, get_session, get_saved_session_statistics, get_vehicle_events,
)

NAVY = '#0D1829'
PANEL = '#172B42'
PANEL2 = '#1D354D'
TEAL = '#37D5C7'
MUTED = '#99B0C6'
WHITE = '#EDF5FB'
PALETTE = ['#25B7AC', '#5B8DEF', '#F0B86B', '#A38CF4', '#E87B94', '#6FBCA3']


def fmt_date(value):
    if not value:
        return '—'
    try:
        return datetime.fromisoformat(str(value)).strftime('%d.%m.%Y. %H:%M:%S')
    except (ValueError, TypeError):
        return str(value)


def fmt_duration(value):
    if value is None:
        return '—'
    try:
        seconds = max(0, int(round(float(value))))
        h, r = divmod(seconds, 3600)
        m, s = divmod(r, 60)
        return f'{h} h {m} min {s} s' if h else f'{m} min {s} s'
    except (ValueError, TypeError):
        return '—'


def safe_text(value):
    return escape('—' if value is None or value == '' else str(value))


def as_count(value):
    try:
        return max(0, int(value))
    except (ValueError, TypeError):
        return 0


def export_traffic_pdf(path, session, stats, events):
    """Profesionalan visestranican PDF; ne cita niti izvozi OCR podatke."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Flowable,
        KeepTogether, HRFlowable,
    )

    font_candidates = [
        Path('C:/Windows/Fonts/segoeui.ttf'),
        Path('C:/Windows/Fonts/arial.ttf'),
        Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'),
    ]
    font_path = next((p for p in font_candidates if p.is_file()), None)
    font = 'Helvetica'
    if font_path:
        font = 'RivaReportUnicode'
        if font not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(TTFont(font, str(font_path)))

    dark = colors.HexColor('#14243B')
    teal = colors.HexColor('#0E9189')
    pale = colors.HexColor('#EAF4F5')
    light = colors.HexColor('#F4F7FB')
    gray = colors.HexColor('#63768C')
    line = colors.HexColor('#DBE6EE')
    page_width, page_height = A4
    usable = 174 * mm

    styles = {
        'hero': ParagraphStyle('RHero', fontName=font, fontSize=19, leading=26, textColor=dark),
        'sub': ParagraphStyle('RSub', fontName=font, fontSize=9, leading=14, textColor=gray),
        'section': ParagraphStyle('RSection', fontName=font, fontSize=11, leading=17, textColor=dark, spaceBefore=10, spaceAfter=8),
        'body': ParagraphStyle('RBody', fontName=font, fontSize=8.5, leading=13, textColor=dark),
        'small': ParagraphStyle('RSmall', fontName=font, fontSize=7.5, leading=11, textColor=dark),
        'white': ParagraphStyle('RWhite', fontName=font, fontSize=7.4, leading=11, textColor=colors.white),
        'note': ParagraphStyle('RNote', fontName=font, fontSize=7.7, leading=12, textColor=gray),
    }

    def para(value, style='small'):
        return Paragraph(safe_text(value), styles[style])

    class MetricCards(Flowable):
        def __init__(self, items):
            super().__init__()
            self.items = items
            self.width = usable
            self.height = 30 * mm

        def draw(self):
            c = self.canv
            gap = 3 * mm
            w = (self.width - 3 * gap) / 4
            for i, (label, value, color) in enumerate(self.items):
                x = i * (w + gap)
                c.setFillColor(colors.HexColor('#F0F5F9'))
                c.roundRect(x, 0, w, self.height, 3 * mm, fill=1, stroke=0)
                c.setFillColor(colors.HexColor(color))
                c.roundRect(x, self.height - 2 * mm, w, 2 * mm, 1 * mm, fill=1, stroke=0)
                c.setFillColor(gray)
                c.setFont(font, 7.1)
                c.drawString(x + 4 * mm, self.height - 10 * mm, label)
                c.setFillColor(dark)
                c.setFont(font, 17)
                c.drawString(x + 4 * mm, 7 * mm, str(value))

    class BarChart(Flowable):
        def __init__(self, data):
            super().__init__()
            self.data = [(str(k), as_count(v)) for k, v in data.items()]
            self.width = usable
            self.height = max(20 * mm, len(self.data) * 13 * mm + 6 * mm)

        def draw(self):
            c = self.canv
            if not self.data:
                c.setFillColor(gray)
                c.setFont(font, 8)
                c.drawString(0, self.height / 2, 'Nema evidentiranih podataka.')
                return
            maximum = max(1, *(v for _, v in self.data))
            for i, (name, value) in enumerate(self.data):
                y = self.height - (i + 1) * 13 * mm + 4 * mm
                c.setFont(font, 8)
                c.setFillColor(dark)
                c.drawString(0, y + 5 * mm, name[:42])
                c.setFillColor(light)
                c.roundRect(0, y, self.width - 17 * mm, 4 * mm, 2 * mm, fill=1, stroke=0)
                if value:
                    c.setFillColor(colors.HexColor(PALETTE[i % len(PALETTE)]))
                    c.roundRect(0, y, (self.width - 17 * mm) * value / maximum, 4 * mm, 2 * mm, fill=1, stroke=0)
                c.setFillColor(dark)
                c.setFont(font, 9)
                c.drawRightString(self.width, y + 0.6 * mm, str(value))

    class DonutChart(Flowable):
        def __init__(self, data):
            super().__init__()
            self.data = [(str(k), as_count(v)) for k, v in data.items() if as_count(v)]
            self.width = usable
            self.height = 43 * mm

        def draw(self):
            c = self.canv
            total = sum(v for _, v in self.data)
            if not total:
                c.setFillColor(gray)
                c.setFont(font, 8)
                c.drawString(0, 20 * mm, 'Nema evidentiranih podataka.')
                return
            cx, cy, r = 25 * mm, 21 * mm, 17 * mm
            start = 90
            for i, (name, value) in enumerate(self.data):
                extent = -360 * value / total
                c.setFillColor(colors.HexColor(PALETTE[i % len(PALETTE)]))
                c.wedge(cx-r, cy-r, cx+r, cy+r, start, extent, stroke=0, fill=1)
                start += extent
            c.setFillColor(colors.white)
            c.circle(cx, cy, 10 * mm, fill=1, stroke=0)
            c.setFillColor(dark)
            c.setFont(font, 13)
            c.drawCentredString(cx, cy - 1.5 * mm, str(total))
            c.setFont(font, 6.5)
            c.setFillColor(gray)
            c.drawCentredString(cx, cy - 6 * mm, 'VOZILA')
            for i, (name, value) in enumerate(self.data):
                x, y = 57 * mm, self.height - 10 * mm - i * 8 * mm
                if y < 2 * mm:
                    break
                c.setFillColor(colors.HexColor(PALETTE[i % len(PALETTE)]))
                c.roundRect(x, y, 4 * mm, 4 * mm, 1 * mm, fill=1, stroke=0)
                c.setFillColor(dark)
                c.setFont(font, 8)
                c.drawString(x + 7 * mm, y + 0.5 * mm, name[:33])
                c.drawRightString(self.width, y + 0.5 * mm, f'{value}  ({value / total * 100:.0f}%)')

    doc = SimpleDocTemplate(
        str(path), pagesize=A4, leftMargin=18*mm, rightMargin=18*mm,
        topMargin=25*mm, bottomMargin=20*mm,
        title=f"RIVA | {session.get('session_code', '')}",
        author='RIVA - Road Intelligence & Vision Analysis',
    )
    code = session.get('session_code') or '—'
    total = as_count(stats.get('total_count', session.get('total_vehicles', 0)))
    correct = as_count(stats.get('correct_count', 0))
    opposite = as_count(stats.get('opposite_count', 0))
    story = [
        Paragraph('IZVJEŠTAJ O ANALIZI CESTOVNOG PROMETA', styles['hero']),
        Paragraph(f"Sesija: {safe_text(code)}  |  Izrađeno: {datetime.now().strftime('%d.%m.%Y. %H:%M')}", styles['sub']),
        Spacer(1, 6*mm),
        MetricCards([
            ('UKUPNO VOZILA', total, '#0E9189'),
            ('ISPRAVAN SMJER', correct, '#5B8DEF'),
            ('SUPROTAN SMJER', opposite, '#E87B94'),
            ('TRAJANJE', fmt_duration(session.get('duration_seconds')), '#A38CF4'),
        ]),
        Spacer(1, 5*mm),
        Paragraph('01  |  PODACI O ANALIZI', styles['section']),
    ]

    def add_table(rows, widths, header=False):
        data = [[para(cell, 'white' if header and row_i == 0 else 'small') for cell in row]
                for row_i, row in enumerate(rows)]
        table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign='LEFT')
        commands = [
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1 if header else 0), (-1, -1), [colors.white, pale]),
            ('LINEBELOW', (0, -1), (-1, -1), 0.5, line),
        ]
        if header:
            commands.append(('BACKGROUND', (0, 0), (-1, 0), dark))
        table.setStyle(TableStyle(commands))
        story.append(table)

    add_table([
        ['Korisnik', session.get('username')],
        ['Izvor', session.get('source_name') or session.get('source_type')],
        ['Vrsta izvora', session.get('source_type')],
        ['Početak obrade', fmt_date(session.get('started_at'))],
        ['Završetak obrade', fmt_date(session.get('finished_at'))],
        ['Trajanje obrade', fmt_duration(session.get('duration_seconds'))],
        ['Status', session.get('status')],
    ], [51*mm, 123*mm])

    lanes = stats.get('lane_counts') or {}
    cats = stats.get('category_counts') or {}
    story.append(Paragraph('02  |  PROMET PO TRAKAMA', styles['section']))
    story.append(BarChart(lanes))
    story.append(Paragraph('03  |  KATEGORIJE VOZILA', styles['section']))
    # Keep chart and its title on same page when possible.
    story.append(DonutChart(cats))
    story.append(Paragraph('04  |  EVIDENCIJA PROLAZAKA', styles['section']))
    if events:
        rows = [['ID', 'Kategorija', 'Traka', 'Smjer', 'Vrijeme prolaska', 'Trajanje']]
        for event in events:
            duration = event.get('duration_seconds')
            try:
                duration_str = f'{float(duration):.2f} s' if duration is not None else '—'
            except (ValueError, TypeError):
                duration_str = '—'
            rows.append([
                event.get('track_id', ''), event.get('vehicle_type', ''),
                event.get('lane', ''), event.get('direction', ''),
                fmt_date(event.get('counted_at')), duration_str,
            ])
        add_table(rows, [14*mm, 29*mm, 21*mm, 34*mm, 52*mm, 24*mm], header=True)
    else:
        story.append(Paragraph('Nema evidentiranih prolazaka.', styles['body']))
    story.extend([
        Spacer(1, 6*mm),
        HRFlowable(width='100%', thickness=.5, color=line),
        Spacer(1, 3*mm),
        Paragraph('Izvještaj je automatski izrađen iz spremljenih podataka sustava RIVA. '
                  'Ne sadrži registarske oznake ni OCR podatke.', styles['note']),
    ])

    def decorate(canvas, document):
        canvas.saveState()
        canvas.setFillColor(dark)
        canvas.rect(0, page_height-13*mm, page_width, 13*mm, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor('#5DE0D6'))
        canvas.setFont(font, 13)
        canvas.drawString(18*mm, page_height-9*mm, '◈ RIVA' if font != 'Helvetica' else 'RIVA')
        canvas.setFillColor(colors.white)
        canvas.setFont(font, 7)
        canvas.drawRightString(page_width-18*mm, page_height-8.5*mm,
                               'ROAD INTELLIGENCE & VISION ANALYSIS')
        canvas.setStrokeColor(line)
        canvas.line(18*mm, 15*mm, page_width-18*mm, 15*mm)
        canvas.setFillColor(gray)
        canvas.setFont(font, 7.2)
        canvas.drawString(18*mm, 10.5*mm, f'RIVA  /  {code}')
        canvas.drawRightString(page_width-18*mm, 10.5*mm, f'Stranica {document.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=decorate, onLaterPages=decorate)


class MetricCard(QFrame):
    def __init__(self, title, color):
        super().__init__()
        self.setObjectName('metricCard')
        self.setStyleSheet(f'''QFrame#metricCard {{background:{PANEL}; border:1px solid #2B4761;
                              border-left:3px solid {color}; border-radius:12px;}}''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(17, 14, 15, 13)
        layout.setSpacing(6)
        label = QLabel(title)
        label.setStyleSheet(f'color:{MUTED}; font-size:11px; font-weight:600; border:none;')
        self.value = QLabel('—')
        self.value.setStyleSheet(f'color:{WHITE}; font-size:26px; font-weight:800; border:none;')
        layout.addWidget(label)
        layout.addWidget(self.value)


class BreakdownPanel(QFrame):
    def __init__(self, title):
        super().__init__()
        self.setObjectName('breakdownPanel')
        self.setStyleSheet(f'''QFrame#breakdownPanel {{background:{PANEL}; border:1px solid #2B4761;
                               border-radius:13px;}}''')
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 17, 18, 18)
        outer.setSpacing(11)
        heading = QLabel(title)
        heading.setStyleSheet(f'color:{WHITE}; font-size:14px; font-weight:bold; border:none;')
        outer.addWidget(heading)
        self.rows = QVBoxLayout()
        self.rows.setSpacing(10)
        outer.addLayout(self.rows)
        outer.addStretch()
        self.update_data({})

    def update_data(self, data):
        while self.rows.count():
            item = self.rows.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        values = [(str(k), as_count(v)) for k, v in (data or {}).items()]
        if not values:
            empty = QLabel('Nema evidentiranih podataka')
            empty.setStyleSheet(f'color:{MUTED}; font-size:12px; border:none;')
            self.rows.addWidget(empty)
            return
        maximum = max(1, *(v for _, v in values))
        for i, (name, value) in enumerate(values):
            container = QWidget()
            container.setStyleSheet("background:transparent; border:none;")
            inner = QVBoxLayout(container)
            inner.setContentsMargins(0, 0, 0, 0)
            inner.setSpacing(5)
            labels = QHBoxLayout()
            left = QLabel(name)
            right = QLabel(str(value))
            left.setStyleSheet(f'background:transparent; border:none; color:{WHITE}; font-size:12px;')
            right.setStyleSheet(f'background:transparent; border:none; color:{TEAL}; font-size:12px; font-weight:bold;')
            labels.addWidget(left)
            labels.addStretch()
            labels.addWidget(right)
            inner.addLayout(labels)
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setRange(0, maximum)
            bar.setValue(value)
            bar.setFixedHeight(8)
            color = PALETTE[i % len(PALETTE)]
            bar.setStyleSheet(f'''QProgressBar {{background:#0C1B2C; border:none; border-radius:4px;}}
                               QProgressBar::chunk {{background:{color}; border-radius:4px;}}''')
            inner.addWidget(bar)
            self.rows.addWidget(container)


class ExportDialog(QDialog):
    def __init__(self, parent, path):
        super().__init__(parent)
        self.setWindowTitle('RIVA | Izvoz završen')
        self.setMinimumWidth(470)
        self.setStyleSheet(f'''QDialog {{background:{NAVY};}}
            QLabel {{color:{WHITE};}}
            QPushButton {{background:#168C86; color:white; border:0; border-radius:9px;
                          padding:11px 22px; font-weight:bold;}}
            QPushButton:hover {{background:#1AA59D;}}''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 26, 28, 25)
        layout.setSpacing(15)
        title = QLabel('✓  PDF izvještaj uspješno izrađen')
        title.setStyleSheet(f'color:{TEAL}; font-size:18px; font-weight:bold;')
        layout.addWidget(title)
        description = QLabel('Izvještaj je spremljen na lokaciju:')
        description.setStyleSheet(f'color:{MUTED};')
        layout.addWidget(description)
        location = QLabel(str(path))
        location.setWordWrap(True)
        location.setTextInteractionFlags(Qt.TextSelectableByMouse)
        location.setStyleSheet(f'background:{PANEL}; border:1px solid #34506A; border-radius:9px; padding:14px;')
        layout.addWidget(location)
        button = QPushButton('U redu')
        button.clicked.connect(self.accept)
        layout.addWidget(button, alignment=Qt.AlignRight)


class ReportsPage(QWidget):
    """Modul Izvjestaji: pregled sesija, statistika, grafikoni i PDF."""
    def __init__(self, username=None):
        super().__init__()
        self.username = username
        self.session_id = None
        self.session = None
        self.stats = {}
        self.events = []
        self.build_ui()
        self.refresh_reports()

    def build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 12, 18, 14)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet('QScrollArea {background:transparent; border:none;}')
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 10, 12, 24)
        layout.setSpacing(13)
        kicker = QLabel('RIVA  /  ANALITIKA I DOKUMENTACIJA')
        kicker.setStyleSheet(f'color:{TEAL}; font-size:10px; font-weight:bold; letter-spacing:1px;')
        layout.addWidget(kicker)
        heading = QLabel('Izvještaji')
        heading.setStyleSheet(f'color:{WHITE}; font-size:30px; font-weight:bold;')
        layout.addWidget(heading)
        subtitle = QLabel('Pregled spremljenih analiza, statistički pokazatelji i profesionalni PDF izvoz')
        subtitle.setStyleSheet(f'color:{MUTED}; font-size:12px;')
        layout.addWidget(subtitle)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet('''
            QTabWidget::pane {border:1px solid #2C4661; border-radius:11px; background:#101F32;}
            QTabBar::tab {background:#1B3046; color:#9FB7CC; padding:12px 20px;
                          margin-right:5px; border-top-left-radius:9px; border-top-right-radius:9px;}
            QTabBar::tab:selected {background:#168C86; color:white; font-weight:bold;}
        ''')
        traffic = QWidget()
        t = QVBoxLayout(traffic)
        t.setContentsMargins(18, 19, 18, 22)
        t.setSpacing(17)
        selector_label = QLabel('ODABIR ANALIZE')
        selector_label.setStyleSheet(f'color:{MUTED}; font-size:10px; font-weight:bold;')
        t.addWidget(selector_label)
        selector_row = QHBoxLayout()
        selector_row.setSpacing(10)
        self.selector = QComboBox()
        self.selector.setMinimumHeight(43)
        self.selector.setStyleSheet('''QComboBox {background:#0B1A2C; color:#F0F7FD;
            border:1px solid #36536F; border-radius:9px; padding:9px 12px;}
            QComboBox QAbstractItemView {background:#1A2F46; color:white;
            selection-background-color:#168C86;}''')
        self.selector.currentIndexChanged.connect(self.load_selected)
        self.refresh_button = QPushButton('↻  Osvježi')
        self.refresh_button.setMinimumHeight(43)
        self.refresh_button.setCursor(Qt.PointingHandCursor)
        self.refresh_button.setStyleSheet('''QPushButton {background:#20374D; color:#DCEBF7;
            border:1px solid #35536B; border-radius:9px; padding:10px 15px;}
            QPushButton:hover {background:#2C4C63;}''')
        self.refresh_button.clicked.connect(self.refresh_reports)
        self.export_button = QPushButton('↓  Izvezi PDF')
        self.export_button.setMinimumHeight(43)
        self.export_button.setCursor(Qt.PointingHandCursor)
        self.export_button.setStyleSheet('''QPushButton {background:#168C86; color:white;
            border:0; border-radius:9px; padding:11px 18px; font-weight:bold;}
            QPushButton:hover {background:#1AA59D;}
            QPushButton:disabled {background:#2A4952; color:#8FA7B5;}''')
        self.export_button.clicked.connect(self.export_pdf)
        selector_row.addWidget(self.selector, 1)
        selector_row.addWidget(self.refresh_button)
        selector_row.addWidget(self.export_button)
        t.addLayout(selector_row)

        self.session_panel = QFrame()
        self.session_panel.setObjectName('sessionPanel')
        self.session_panel.setStyleSheet(f'''QFrame#sessionPanel {{background:{PANEL};
            border:1px solid #2D4A65; border-radius:12px;}}''')
        details_layout = QVBoxLayout(self.session_panel)
        details_layout.setContentsMargins(18, 16, 18, 16)
        details_layout.setSpacing(10)
        details_heading = QLabel('PODACI O SESIJI')
        details_heading.setStyleSheet(f'color:{TEAL}; font-size:10px; font-weight:bold; border:none;')
        details_layout.addWidget(details_heading)
        grid = QGridLayout()
        grid.setHorizontalSpacing(28)
        grid.setVerticalSpacing(12)
        self.info_values = {}
        for i, (key, label) in enumerate([
            ('code', 'OZNAKA SESIJE'), ('username', 'KORISNIK'),
            ('source', 'IZVOR ANALIZE'), ('status', 'STATUS'),
            ('start', 'POČETAK'), ('finish', 'ZAVRŠETAK'),
        ]):
            cell = QWidget()
            cell.setStyleSheet("background: transparent; border: none;")
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(3)
            k = QLabel(label)
            k.setStyleSheet(f'background:transparent; border:none; color:{MUTED}; font-size:10px; font-weight:bold;')
            v = QLabel('—')
            v.setTextInteractionFlags(Qt.TextSelectableByMouse)
            v.setStyleSheet(f'background:transparent; border:none; color:{WHITE}; font-size:12px; font-weight:600;')
            cell_layout.addWidget(k)
            cell_layout.addWidget(v)
            grid.addWidget(cell, i // 3, i % 3)
            self.info_values[key] = v
        details_layout.addLayout(grid)
        t.addWidget(self.session_panel)

        metrics = QGridLayout()
        metrics.setSpacing(11)
        self.cards = [
            MetricCard('UKUPNO VOZILA', '#25B7AC'),
            MetricCard('ISPRAVAN SMJER', '#5B8DEF'),
            MetricCard('SUPROTAN SMJER', '#E87B94'),
            MetricCard('TRAJANJE OBRADE', '#A38CF4'),
        ]
        for i, card in enumerate(self.cards):
            metrics.addWidget(card, i // 2, i % 2)
        t.addLayout(metrics)

        breakdowns = QHBoxLayout()
        breakdowns.setSpacing(12)
        self.lane_panel = BreakdownPanel('Promet po trakama')
        self.category_panel = BreakdownPanel('Kategorije vozila')
        breakdowns.addWidget(self.lane_panel, 1)
        breakdowns.addWidget(self.category_panel, 1)
        t.addLayout(breakdowns)

        table_header = QHBoxLayout()
        label = QLabel('Detaljna evidencija prolazaka')
        label.setStyleSheet(f'color:{WHITE}; font-size:17px; font-weight:bold;')
        self.event_count = QLabel('0 zapisa')
        self.event_count.setStyleSheet(f'color:{MUTED}; font-size:11px;')
        table_header.addWidget(label)
        table_header.addStretch()
        table_header.addWidget(self.event_count)
        t.addLayout(table_header)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            'ID vozila', 'Kategorija', 'Traka', 'Smjer', 'Vrijeme prolaska', 'Trajanje (s)',
        ])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().hide()
        self.table.verticalHeader().setDefaultSectionSize(38)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setMinimumHeight(280)
        self.table.setStyleSheet('''QTableWidget {background:#0C1B2D;
            alternate-background-color:#172A40; color:#E5F0F8;
            border:1px solid #2D4862; border-radius:9px;
            gridline-color:#2B4258; selection-background-color:#176C72;}
            QHeaderView::section {background:#203B53; color:#EAF5FC;
            padding:11px 7px; border:none; font-weight:bold;}''')
        t.addWidget(self.table)
        self.tabs.addTab(traffic, 'Prometni izvještaji')

        ocr = QWidget()
        ocr_layout = QVBoxLayout(ocr)
        ocr_layout.setContentsMargins(25, 25, 25, 25)
        ocr_layout.setSpacing(14)

        ocr_title = QLabel("OCR IZVJE\u0160\u0106A")
        ocr_title.setStyleSheet(
            f"color:{TEAL}; font-size:19px; font-weight:bold;"
        )
        ocr_layout.addWidget(ocr_title)

        ocr_session_label = QLabel("ODABIR ANALIZE")
        ocr_session_label.setStyleSheet(
            f"color:{MUTED}; font-size:12px; font-weight:bold;"
        )
        ocr_layout.addWidget(ocr_session_label)

        self.ocr_selector = QComboBox()
        self.ocr_selector.setMinimumHeight(42)
        self.ocr_selector.currentIndexChanged.connect(
            lambda _: self.refresh_ocr_table()
        )
        ocr_layout.addWidget(self.ocr_selector)

        self.ocr_mode = QComboBox()
        self.ocr_mode.addItem("Javni prikaz", False)

        from core.users import get_user_role
        if get_user_role(self.username) == "admin":
            self.ocr_mode.addItem("Interni prikaz", True)

        self.ocr_mode.currentIndexChanged.connect(
            lambda _: self.refresh_ocr_table()
        )
        ocr_layout.addWidget(self.ocr_mode)

        # OCR statistika
        self.ocr_stat_cards = []

        ocr_stats_row = QHBoxLayout()
        ocr_stats_row.setSpacing(12)

        stat_definitions = [
            ("UKUPNO PROLAZAKA", "#21B7B2"),
            ("POTVR\u0110ENO", "#4F8DF7"),
            ("ODBIJENO", "#E87991"),
            ("NA PROVJERI", "#A78BFA"),
        ]

        for title, color in stat_definitions:
            card = QFrame()
            card.setMinimumHeight(100)
            card.setStyleSheet(
                "QFrame {"
                "background:#1A3048;"
                "border:1px solid #29445F;"
                "border-left:4px solid " + color + ";"
                "border-radius:9px;"
                "}"
            )

            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(15, 12, 15, 12)

            heading = QLabel(title)
            heading.setStyleSheet(
                "color:#9BB4C9; font-size:11px;"
                "font-weight:bold; border:none;"
            )

            value = QLabel("0")
            value.setStyleSheet(
                "color:#F0F7FC; font-size:28px;"
                "font-weight:bold; border:none;"
            )

            card_layout.addWidget(heading)
            card_layout.addWidget(value)
            card_layout.addStretch()

            ocr_stats_row.addWidget(card)
            self.ocr_stat_cards.append(value)

        ocr_layout.addLayout(ocr_stats_row)

        ocr_table_title = QLabel(
            "DETALJNA EVIDENCIJA OCR O\u010cITANJA"
        )
        ocr_table_title.setStyleSheet(
            "color:#EAF5FC; font-size:15px; font-weight:bold;"
        )
        ocr_layout.addWidget(ocr_table_title)


        # Jedan PDF gumb prati odabrani OCR prikaz.
        ocr_pdf_row = QHBoxLayout()
        ocr_pdf_row.addStretch()

        self.ocr_pdf_button = QPushButton()
        self.ocr_pdf_button.setMinimumHeight(43)
        self.ocr_pdf_button.setMinimumWidth(205)
        self.ocr_pdf_button.setCursor(Qt.PointingHandCursor)
        self.ocr_pdf_button.setStyleSheet("""
            QPushButton {
                background-color: #159B98;
                color: #FFFFFF;
                border: 1px solid #21B8B3;
                border-radius: 8px;
                padding: 10px 22px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #20B5AF;
            }
            QPushButton:pressed {
                background-color: #117D7A;
            }
        """)

        self.ocr_pdf_button.clicked.connect(
            lambda: self.export_ocr_pdf(
                bool(self.ocr_mode.currentData())
            )
        )

        ocr_pdf_row.addWidget(self.ocr_pdf_button)
        ocr_layout.addLayout(ocr_pdf_row)



        self.ocr_mode.currentIndexChanged.connect(
            lambda _: self.update_ocr_pdf_button()
        )
        self.update_ocr_pdf_button()

        self.ocr_table = QTableWidget()
        self.ocr_table.setColumnCount(7)
        self.ocr_table.setHorizontalHeaderLabels([
            "ID", "Vrijeme", "Vrsta vozila",
            "Traka", "Smjer", "Registracija", "Status"
        ])
        self.ocr_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.ocr_table.setEditTriggers(
            QAbstractItemView.NoEditTriggers
        )
        self.ocr_table.setSelectionBehavior(
            QAbstractItemView.SelectRows
        )
        self.ocr_table.setAlternatingRowColors(True)
        self.ocr_table.verticalHeader().hide()
        ocr_layout.addWidget(self.ocr_table)

        self.ocr_info = QLabel("")
        self.ocr_info.setStyleSheet(f"color:{MUTED};")
        ocr_layout.addWidget(self.ocr_info)

        self.tabs.addTab(
            ocr, "OCR izvje\u0161taji"
        )
        self.selector.currentIndexChanged.connect(
            lambda _: self.refresh_ocr_table()
        )

        self.tabs.currentChanged.connect(
            lambda _: self.refresh_ocr_table()
            if self.tabs.currentWidget() == ocr else None
        )
        layout.addWidget(self.tabs)
        scroll.setWidget(content)
        outer.addWidget(scroll)

    def update_ocr_pdf_button(self):
        internal = bool(self.ocr_mode.currentData())

        if internal:
            self.ocr_pdf_button.setText(
                "Izvezi interni PDF"
            )
        else:
            self.ocr_pdf_button.setText(
                "Izvezi javni PDF"
            )

    def export_ocr_pdf(self, internal):
        from pathlib import Path
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        from core.ocr_pdf import export_ocr_pdf

        sid = self.ocr_selector.currentData()

        if sid is None:
            QMessageBox.warning(
                self, "RIVA", "Odaberi OCR sesiju."
            )
            return

        mode = "interni" if internal else "javni"
        filename = f"RIVA-{int(sid):06d}_OCR_{mode}.pdf"

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Spremi OCR izvje??e",
            str(Path.home() / "Documents" / filename),
            "PDF datoteke (*.pdf)"
        )

        if not path:
            return

        if not path.lower().endswith(".pdf"):
            path += ".pdf"

        try:
            export_ocr_pdf(
                path, self.username, sid, internal=internal
            )
        except Exception as exc:
            QMessageBox.critical(
                self, "RIVA | OCR PDF",
                f"Izvoz nije uspio: {exc}"
            )
            return

        # Evidencija uspjesno izvezenog OCR izvjestaja.
        from core.audit import log_event

        try:
            log_event(
                event_type=(
                    "OCR_INTERNAL_EXPORTED"
                    if internal else "OCR_PUBLIC_EXPORTED"
                ),
                username=self.username,
                description=(
                    "Uspjesno izvezen "
                    + ("interni" if internal else "javni")
                    + " OCR PDF. Sesija: "
                    + str(sid)
                    + "."
                ),
                status="SUCCESS"
            )
        except Exception as audit_error:
            print(
                "Upozorenje: OCR PDF je spremljen, ali "
                "evidencija nije azurirana: "
                + str(audit_error)
            )

        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton

        dialog = QDialog(self)
        dialog.setWindowTitle("RIVA | Izvoz zavr\u0161en")
        dialog.setFixedWidth(470)
        dialog.setStyleSheet("""
            QDialog {
                background:#0B1627;
                color:#EAF5FC;
            }
            QLabel {
                color:#EAF5FC;
                border:none;
            }
            QPushButton {
                background:#159B98;
                color:white;
                border:none;
                border-radius:8px;
                padding:11px 25px;
                font-weight:bold;
                min-width:80px;
            }
            QPushButton:hover {
                background:#20B5AF;
            }
        """)

        content = QVBoxLayout(dialog)
        content.setContentsMargins(28, 26, 28, 24)
        content.setSpacing(17)

        heading = QLabel(
            "\u2713  PDF izvje\u0161\u0107e uspje\u0161no izra\u0111eno"
        )
        heading.setStyleSheet(
            "color:#35D0C8; font-size:18px; font-weight:bold;"
        )
        content.addWidget(heading)

        description = QLabel(
            "Izvje\u0161\u0107e je spremljeno na lokaciju:"
        )
        description.setStyleSheet("color:#9BB4C9; font-size:12px;")
        content.addWidget(description)

        location = QLabel(str(path))
        location.setWordWrap(True)
        location.setTextInteractionFlags(Qt.TextSelectableByMouse)
        location.setStyleSheet("""
            background:#1A3048;
            border:1px solid #2D4862;
            border-radius:8px;
            padding:13px;
            color:#EAF5FC;
            font-size:11px;
        """)
        content.addWidget(location)

        buttons = QHBoxLayout()
        buttons.addStretch()

        ok_button = QPushButton("U redu")
        ok_button.clicked.connect(dialog.accept)
        buttons.addWidget(ok_button)
        content.addLayout(buttons)

        dialog.exec()

    def refresh_ocr_table(self):
        """Osvjezi OCR podatke za odabranu sesiju."""
        self.ocr_table.setRowCount(0)
        for card in self.ocr_stat_cards:
            card.setText("0")

        session_id = self.ocr_selector.currentData()
        if session_id is None:
            self.ocr_info.setText("Nije odabrana sesija.")
            return

        internal = bool(self.ocr_mode.currentData())

        try:
            rows = get_ocr_report(
                self.username,
                session_id,
                internal=internal
            )
        except Exception as exc:
            self.ocr_info.setText(
                "Greška pri u?itavanju OCR podataka: "
                + str(exc)
            )
            return

        statuses = {
            "PENDING": "Na provjeri",
            "CONFIRMED": "Potvrđeno",
            "REJECTED": "Ručno odbačeno"
        }

        confirmed = sum(
            r.get("review_status") == "CONFIRMED" for r in rows
        )
        rejected = sum(
            r.get("review_status") == "REJECTED" for r in rows
        )
        pending = sum(
            r.get("review_status") == "PENDING" for r in rows
        )

        for card, value in zip(
            self.ocr_stat_cards,
            [len(rows), confirmed, rejected, pending]
        ):
            card.setText(str(value))

        self.ocr_table.setRowCount(len(rows))

        for row_index, item in enumerate(rows):
            values = [
                item.get("id"),
                fmt_date(item.get("counted_at")),
                item.get("vehicle_type"),
                item.get("lane"),
                item.get("direction"),
                (
                    "Odbačeno"
                    if item.get("review_status") == "REJECTED"
                    else item.get("registration_text")
                ),
                (
                    "Ručno potvrđeno"
                    if item.get("review_status") == "CONFIRMED"
                    and item.get("entry_source") in (
                        "MANUAL_ENTRY",
                        "MANUAL_CORRECTION",
                        "MANUAL_CONFIRMATION"
                    )
                    else statuses.get(
                        item.get("review_status"),
                        "Nije obrađeno"
                    )
                )
            ]

            for col_index, value in enumerate(values):
                cell = QTableWidgetItem(
                    str(value) if value is not None else "-"
                )
                self.ocr_table.setItem(
                    row_index, col_index, cell
                )

        self.ocr_info.setText(
            f"Ukupno prolazaka: {len(rows)} | "
            + ("Interni prikaz" if internal else "Javni prikaz")
        )

    def refresh_reports(self):
        previous = self.selector.currentData()
        try:
            sessions = get_recent_sessions(limit=200)
        except Exception as exc:
            QMessageBox.warning(self, 'RIVA | Izvještaji', f'Ne mogu učitati sesije: {exc}')
            return
        self.selector.blockSignals(True)
        self.selector.clear()
        self.selector.addItem(
            "Odaberite analizu za prikaz izvjestaja...", None
        )
        for session in sessions:
            sid = session.get('id')
            if sid is None:
                continue
            code = session.get('session_code') or f'RIVA-{sid:06d}'
            label = f"{code}  •  {fmt_date(session.get('started_at'))}  •  {session.get('username', '—')}"
            self.selector.addItem(label, sid)
        if not self.selector.count():
            self.selector.addItem('Nema dostupnih analiza', None)
        idx = self.selector.findData(previous)
        self.selector.setCurrentIndex(idx if idx >= 0 else 0)
        self.selector.setEnabled(bool(sessions))
        self.selector.blockSignals(False)

        self.ocr_selector.blockSignals(True)
        previous_ocr = self.ocr_selector.currentData()
        self.ocr_selector.clear()
        self.ocr_selector.addItem(
            "Odaberite sesiju za OCR izvjestaj...", None
        )

        for session in sessions:
            sid = session.get("id")
            if sid is None:
                continue
            code = session.get("session_code") or f"RIVA-{sid:06d}"
            label = (
                f"{code}  |  "
                f"{fmt_date(session.get('started_at'))}  |  "
                f"{session.get('username') or '-'}"
            )
            self.ocr_selector.addItem(label, sid)

        index = self.ocr_selector.findData(previous_ocr)
        self.ocr_selector.setCurrentIndex(
            index if index >= 0 else 0
        )
        self.ocr_selector.blockSignals(False)

        self.load_selected()
        self.refresh_ocr_table()

    def load_selected(self, *_):
        sid = self.selector.currentData()
        self.session_id = None
        self.session = None
        self.stats = {}
        self.events = []
        self.export_button.setEnabled(False)
        self.table.setRowCount(0)
        if sid is None:
            self.set_empty()
            return
        try:
            session = get_session(sid)
            if session is None:
                raise ValueError('Odabrana sesija ne postoji.')
            stats = get_saved_session_statistics(sid) or {}
            events = get_vehicle_events(sid)
        except Exception as exc:
            self.set_empty()
            QMessageBox.warning(self, 'RIVA | Izvještaji', f'Ne mogu učitati izvještaj: {exc}')
            return
        self.session_id, self.session, self.stats, self.events = sid, session, stats, events
        details = {
            'code': session.get('session_code') or '—',
            'username': session.get('username') or '—',
            'source': session.get('source_name') or session.get('source_type') or '—',
            'status': session.get('status') or '—',
            'start': fmt_date(session.get('started_at')),
            'finish': fmt_date(session.get('finished_at')),
        }
        for key, value in details.items():
            self.info_values[key].setText(str(value))
        for card, value in zip(self.cards, [
            stats.get('total_count', session.get('total_vehicles', 0)),
            stats.get('correct_count', 0),
            stats.get('opposite_count', 0),
            fmt_duration(session.get('duration_seconds')),
        ]):
            card.value.setText(str(value))
        self.lane_panel.update_data(stats.get('lane_counts') or {})
        self.category_panel.update_data(stats.get('category_counts') or {})
        self.event_count.setText(f'{len(events)} zapisa')
        self.table.setRowCount(len(events))
        for row, event in enumerate(events):
            duration = event.get('duration_seconds')
            try:
                duration_str = f'{float(duration):.2f}' if duration is not None else '—'
            except (ValueError, TypeError):
                duration_str = '—'
            values = [
                event.get('track_id', ''), event.get('vehicle_type', ''),
                event.get('lane', ''), event.get('direction', ''),
                fmt_date(event.get('counted_at')), duration_str,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(row, col, item)
        self.export_button.setEnabled(True)

    def set_empty(self):
        for value in self.info_values.values():
            value.setText('—')
        for card in self.cards:
            card.value.setText('—')
        self.lane_panel.update_data({})
        self.category_panel.update_data({})
        self.event_count.setText('0 zapisa')

    def export_pdf(self):
        if self.session is None:
            return
        code = self.session.get('session_code') or f'RIVA-{self.session_id:06d}'
        path, _ = QFileDialog.getSaveFileName(
            self, 'Spremi prometni izvještaj',
            str(Path.home() / f'{code}_prometni_izvjestaj.pdf'),
            'PDF dokument (*.pdf)',
        )
        if not path:
            return
        if not path.lower().endswith('.pdf'):
            path += '.pdf'
        try:
            export_traffic_pdf(path, self.session, self.stats, self.events)
        except Exception as exc:
            QMessageBox.critical(self, 'RIVA | PDF izvoz', f'Izvoz nije uspio: {exc}')
            return
        from core.audit import log_event

        try:
            log_event(
                event_type="TRAFFIC_REPORT_EXPORTED",
                username=self.username,
                description=(
                    "Uspjesno izraden standardni prometni izvjestaj. "
                    f"Sesija: {code}. Format: PDF."
                ),
                status="SUCCESS"
            )
        except Exception as audit_error:
            print(
                "Upozorenje: PDF je spremljen, ali evidencija "
                f"nije azurirana: {audit_error}"
            )

        ExportDialog(self, path).exec()
