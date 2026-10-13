# pdf_export.py
# Генерация PDF через fpdf2 в стиле сайта: тёмный корпоративный отчёт,
# сегментная шкала риска, моно-шрифт для цифр. Для печати есть светлая тема.
#
# Шрифты: положите рядом с файлом (или в папку fonts/)
#   DejaVuSans.ttf, DejaVuSans-Bold.ttf, DejaVuSansMono.ttf, DejaVuSansMono-Bold.ttf
# Если файла нет, берётся системный DejaVu, а при его отсутствии — запасной вариант
# (жирный -> обычный, моно -> обычный).

import os
from datetime import datetime

from fpdf import FPDF
from fpdf.enums import XPos, YPos

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_DIRS = [
    HERE,
    os.path.join(HERE, "fonts"),
    "/usr/share/fonts/truetype/dejavu",
    "/usr/share/fonts/dejavu",
    "/Library/Fonts",
    "C:\\Windows\\Fonts",
]

# --- Темы (RGB) ---
THEMES = {
    "dark": {
        "bg":      (15, 19, 24),
        "panel":   (22, 27, 34),
        "panel2":  (28, 35, 44),
        "border":  (40, 49, 60),
        "text":    (232, 236, 241),
        "body":    (195, 204, 215),
        "muted":   (143, 154, 168),
        "accent":  (122, 167, 224),
        "red":     (229, 83, 75),
        "orange":  (224, 138, 60),
        "yellow":  (212, 176, 58),
        "green":   (76, 175, 122),
        "warn_bg": (47, 25, 27),
    },
    "light": {
        "bg":      (255, 255, 255),
        "panel":   (245, 247, 250),
        "panel2":  (245, 247, 250),
        "border":  (220, 224, 230),
        "text":    (25, 30, 38),
        "body":    (55, 65, 78),
        "muted":   (120, 130, 142),
        "accent":  (61, 106, 168),
        "red":     (200, 60, 55),
        "orange":  (200, 120, 45),
        "yellow":  (180, 150, 40),
        "green":   (60, 150, 105),
        "warn_bg": (250, 235, 235),
    },
}

M = 18          # поля, мм
W = 210 - 2 * M  # ширина контента

# Человекочитаемые подписи ответов формы
ANSWER_LABELS = {
    "providers": ("Облачные провайдеры", {
        "one": "Один", "two": "Два", "three_plus": "Три и более"}),
    "failover": ("Резервный провайдер", {
        "no": "Нет", "cold": "Холодный", "hot": "Горячий"}),
    "data_location": ("Критичные данные", {
        "single_cloud": "В одном облаке",
        "multi_cloud": "В нескольких облаках",
        "on_prem_backup": "Есть локальный бэкап"}),
    "downtime": ("Допустимый простой", {
        "less_than_4h": "Меньше 4 часов", "4_to_24h": "От 4 до 24 часов",
        "days": "Несколько дней", "weeks_ok": "Недели"}),
    "gpu": ("GPU/ML-нагрузки", {
        "no": "Нет", "yes_noncritical": "Да, не критично",
        "yes_critical": "Да, критично"}),
}


def _find_font(*names):
    for name in names:
        for d in FONT_DIRS:
            p = os.path.join(d, name)
            if os.path.isfile(p):
                return p
    return None


def _resolve_fonts():
    sans = _find_font("DejaVuSans.ttf")
    if not sans:
        raise FileNotFoundError(
            "Не найден DejaVuSans.ttf. Положите его рядом с pdf_export.py "
            "или в папку fonts/.")
    sans_b = _find_font("DejaVuSans-Bold.ttf") or sans
    mono = _find_font("DejaVuSansMono.ttf") or sans
    mono_b = _find_font("DejaVuSansMono-Bold.ttf") or mono
    return sans, sans_b, mono, mono_b


class ReportPDF(FPDF):
    def __init__(self, theme: dict):
        super().__init__(orientation="P", unit="mm", format="A4")
        self.t = theme
        self.set_margins(M, 18, M)
        self.set_auto_page_break(auto=True, margin=22)
        self.alias_nb_pages()

        sans, sans_b, mono, mono_b = _resolve_fonts()
        self.add_font("Sans", "", sans)
        self.add_font("Sans", "B", sans_b)
        self.add_font("Mono", "", mono)
        self.add_font("Mono", "B", mono_b)

    # --- шапка каждой страницы: фон + бренд ---
    def header(self):
        t = self.t
        self.set_fill_color(*t["bg"])
        self.rect(0, 0, self.w, self.h, style="F")

        # логотип: квадрат с рамкой и заливкой внутри
        self.set_draw_color(*t["accent"])
        self.set_line_width(0.5)
        self.rect(M, 11, 4.4, 4.4, style="D")
        self.set_fill_color(*t["accent"])
        self.rect(M + 1.2, 12.2, 2, 2, style="F")

        self.set_xy(M + 7.5, 10.6)
        _font(self, "Sans", "B", 9.5, t["text"])
        self.cell(40, 5, "Cloud Audit")

        self.set_xy(M, 10.8)
        _font(self, "Mono", "", 8, t["muted"])
        self.cell(W, 5, datetime.now().strftime("%d.%m.%Y"), align="R")

        self.set_draw_color(*t["border"])
        self.set_line_width(0.25)
        self.line(M, 19, self.w - M, 19)
        self.set_xy(M, 28)

    def footer(self):
        t = self.t
        self.set_draw_color(*t["border"])
        self.set_line_width(0.25)
        self.line(M, self.h - 16, self.w - M, self.h - 16)

        self.set_xy(M, self.h - 12.5)
        _font(self, "Sans", "", 7.5, t["muted"])
        self.cell(130, 4, "Cloud Dependency Audit. Отчёт носит рекомендательный характер")

        self.set_xy(M, self.h - 12.5)
        _font(self, "Mono", "", 7.5, t["muted"])
        self.cell(W, 4, f"{self.page_no()} / {{nb}}", align="R")


# ---------------------------------------------------------------
# Хелперы
# ---------------------------------------------------------------
def _font(pdf, family, style, size, color):
    pdf.set_font(family, style, size)
    pdf.set_text_color(*color)


def _risk_color(theme: dict, risk_color: str) -> tuple:
    return theme.get(risk_color if risk_color in ("red", "orange", "yellow", "green") else "muted")


def _need(pdf, h):
    """Перенос на новую страницу, если блок высотой h не помещается."""
    if pdf.get_y() + h > pdf.h - 22:
        pdf.add_page()


def _mc_height(pdf, w, line_h, text) -> float:
    """Высота многострочного текста без отрисовки (шрифт уже выставлен)."""
    try:
        return pdf.multi_cell(w, line_h, text, dry_run=True, output="HEIGHT")
    except TypeError:  # старые версии fpdf2
        lines = pdf.multi_cell(w, line_h, text, split_only=True)
        return len(lines) * line_h


def _mc(pdf, x, y, w, line_h, text):
    pdf.set_xy(x, y)
    pdf.multi_cell(w, line_h, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _box(pdf, x, y, w, h, fill, border):
    pdf.set_fill_color(*fill)
    pdf.set_draw_color(*border)
    pdf.set_line_width(0.25)
    pdf.rect(x, y, w, h, style="DF")


def _section(pdf, text, gap=8):
    _need(pdf, 26)
    pdf.set_y(pdf.get_y() + gap)
    _font(pdf, "Sans", "B", 12, pdf.t["text"])
    pdf.set_x(M)
    pdf.cell(W, 7, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    y = pdf.get_y() + 1
    pdf.set_draw_color(*pdf.t["border"])
    pdf.set_line_width(0.25)
    pdf.line(M, y, M + W, y)
    pdf.set_y(y + 4)


def _bullets(pdf, items, color, size=10, line_h=5, fg=None, rules=True):
    t = pdf.t
    fg = fg or t["body"]
    for i, text in enumerate(items):
        _font(pdf, "Sans", "", size, fg)
        h = _mc_height(pdf, W - 6, line_h, text)
        _need(pdf, h + 6)
        y = pdf.get_y()
        pdf.set_fill_color(*color)
        pdf.rect(M, y + 2.2, 1.7, 1.7, style="F")
        _mc(pdf, M + 6, y + 1, W - 6, line_h, text)
        y_end = y + h + 2.5
        if rules and i < len(items) - 1:
            pdf.set_draw_color(*t["border"])
            pdf.set_line_width(0.2)
            pdf.line(M, y_end, M + W, y_end)
        pdf.set_y(y_end + 1.5)


def _tile(pdf, x, y, w, h, label, value, note):
    t = pdf.t
    _box(pdf, x, y, w, h, t["panel2"], t["border"])

    pdf.set_xy(x + 4, y + 4)
    _font(pdf, "Mono", "B", 8, t["accent"])
    pdf.cell(w - 8, 4, label)

    # значение: уменьшаем кегль, пока не влезет в плитку
    size = 14
    _font(pdf, "Mono", "B", size, t["text"])
    while size > 8 and pdf.get_string_width(value) > w - 8:
        size -= 0.5
        pdf.set_font("Mono", "B", size)
    pdf.set_xy(x + 4, y + 10)
    pdf.cell(w - 8, 8, value)

    _font(pdf, "Sans", "", 7, t["muted"])
    _mc(pdf, x + 4, y + 20, w - 8, 3.5, note)


def _answers_table(pdf, answers):
    t = pdf.t
    rows = []
    for key, (label, mapping) in ANSWER_LABELS.items():
        raw = answers.get(key) if hasattr(answers, "get") else None
        if raw is None:
            continue
        rows.append((label, mapping.get(raw, str(raw))))
    if not rows:
        return

    _section(pdf, "Параметры инфраструктуры")
    row_h = 8
    _need(pdf, row_h * len(rows) + 2)
    for i, (label, value) in enumerate(rows):
        y = pdf.get_y()
        pdf.set_xy(M, y + 1.2)
        _font(pdf, "Sans", "", 9.5, t["muted"])
        pdf.cell(W / 2, 5.5, label)
        pdf.set_xy(M + W / 2, y + 1.2)
        _font(pdf, "Mono", "", 9, t["text"])
        pdf.cell(W / 2, 5.5, value, align="R")
        if i < len(rows) - 1:
            pdf.set_draw_color(*t["border"])
            pdf.set_line_width(0.2)
            pdf.line(M, y + row_h, M + W, y + row_h)
        pdf.set_y(y + row_h)


# ---------------------------------------------------------------
# Основная функция
# ---------------------------------------------------------------
def generate_report_pdf(risk_data: dict, recommendations: list, answers: dict,
                        bia_data: dict = None, theme: str = "dark") -> bytes:
    t = THEMES.get(theme, THEMES["dark"])
    pdf = ReportPDF(t)
    pdf.set_title("Аудит облачной зависимости")
    pdf.set_author("Cloud Dependency Audit")
    pdf.set_creator("Cloud Dependency Audit")
    pdf.add_page()

    risk = _risk_color(t, risk_data["risk_color"])

    # ============================
    # ЗАГОЛОВОК
    # ============================
    _font(pdf, "Sans", "B", 22, t["text"])
    pdf.set_x(M)
    pdf.cell(W, 11, "Аудит облачной зависимости", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    _font(pdf, "Sans", "", 10, t["muted"])
    pdf.set_x(M)
    pdf.cell(W, 6, "Оценка устойчивости инфраструктуры к сбою облачного провайдера",
             new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_y(pdf.get_y() + 8)

    # ============================
    # ПАНЕЛЬ РЕЗУЛЬТАТА + СЕГМЕНТНАЯ ШКАЛА
    # ============================
    y0 = pdf.get_y()
    panel_h = 40
    _box(pdf, M, y0, W, panel_h, t["panel"], t["border"])
    pdf.set_fill_color(*risk)
    pdf.rect(M, y0, W, 1.4, style="F")  # верхняя полоса цвета риска

    pdf.set_xy(M + 7, y0 + 8)
    _font(pdf, "Sans", "B", 20, risk)
    pdf.cell(W / 2, 10, f"Риск: {risk_data['risk_level']}")

    pdf.set_xy(M + W / 2, y0 + 10)
    _font(pdf, "Mono", "", 10, t["muted"])
    pdf.cell(W / 2 - 7, 7,
             f"{risk_data['score']} / {risk_data['max_score']} баллов, {risk_data['percentage']}%",
             align="R")

    seg_total, gap = 20, 1.0
    inner = W - 14
    seg_w = (inner - gap * (seg_total - 1)) / seg_total
    on_count = max(0, min(seg_total, int(float(risk_data["percentage"]) // 5)))
    y_seg = y0 + 24
    for i in range(seg_total):
        x = M + 7 + i * (seg_w + gap)
        if i < on_count:
            pdf.set_fill_color(*risk)
            pdf.set_draw_color(*risk)
        else:
            pdf.set_fill_color(*t["panel2"])
            pdf.set_draw_color(*t["border"])
        pdf.set_line_width(0.2)
        pdf.rect(x, y_seg, seg_w, 8, style="DF")
    pdf.set_y(y0 + panel_h)

    # ============================
    # ОТВЕТЫ
    # ============================
    if answers:
        _answers_table(pdf, answers)

    # ============================
    # BIA
    # ============================
    if bia_data:
        _section(pdf, "Business Impact Analysis")

        gap_t = 3
        tile_w = (W - 3 * gap_t) / 4
        tile_h = 30
        _need(pdf, tile_h + 6)
        y = pdf.get_y()
        tiles = [
            ("MTPD", bia_data["mtpd"]["label"], "Максимально допустимый простой"),
            ("RTO", f"{bia_data['rto_hours']} ч", "Целевое время восстановления"),
            ("RPO", f"{bia_data['rpo_hours']} ч", "Допустимая потеря данных"),
            ("Потери", f"{bia_data['loss_per_hour']:,} ₽".replace(",", " "), "Оценка потерь за час"),
        ]
        for i, (label, value, note) in enumerate(tiles):
            _tile(pdf, M + i * (tile_w + gap_t), y, tile_w, tile_h, label, value, note)
        pdf.set_y(y + tile_h + 6)

        # Предупреждение, если RTO > MTPD
        if bia_data["rto_hours"] > bia_data["mtpd"]["mtpd_hours"]:
            msg = (f"Целевое время восстановления ({bia_data['rto_hours']} ч) превышает "
                   f"допустимый простой ({bia_data['mtpd']['label']}). "
                   f"При сбое вы не успеете восстановиться в пределах допустимого.")
            _font(pdf, "Sans", "", 8.5, t["body"])
            msg_h = _mc_height(pdf, W - 14, 4.2, msg)
            box_h = msg_h + 15
            _need(pdf, box_h + 4)
            yw = pdf.get_y()
            _box(pdf, M, yw, W, box_h, t["warn_bg"], t["red"])
            pdf.set_fill_color(*t["red"])
            pdf.rect(M, yw, 1.4, box_h, style="F")
            pdf.set_xy(M + 7, yw + 3.5)
            _font(pdf, "Sans", "B", 9.5, t["red"])
            pdf.cell(W - 14, 5, "Критическое несоответствие RTO и MTPD")
            _font(pdf, "Sans", "", 8.5, t["body"])
            _mc(pdf, M + 7, yw + 9.5, W - 14, 4.2, msg)
            pdf.set_y(yw + box_h + 6)

        # Операционные последствия
        if bia_data.get("consequences"):
            _need(pdf, 20)
            _font(pdf, "Sans", "B", 10.5, t["text"])
            pdf.set_x(M)
            pdf.cell(W, 6, "Операционные последствия при сбое",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1.5)
            _bullets(pdf, bia_data["consequences"], risk)

        # Комментарии по RTO/RPO
        notes = [bia_data[k] for k in ("rto_note", "rpo_note", "loss_note") if bia_data.get(k)]
        if notes:
            pdf.set_y(pdf.get_y() + 4)
            _need(pdf, 20)
            _font(pdf, "Sans", "B", 10.5, t["text"])
            pdf.set_x(M)
            pdf.cell(W, 6, "Комментарии по RTO и RPO",
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(1.5)
            _bullets(pdf, notes, t["accent"], size=9, line_h=4.5, fg=t["muted"], rules=False)

    # ============================
    # ЧТО ПОВЛИЯЛО НА ОЦЕНКУ
    # ============================
    _section(pdf, "Что повлияло на оценку")
    _bullets(pdf, risk_data["details"], risk)

    # ============================
    # РЕКОМЕНДАЦИИ
    # ============================
    if recommendations:
        _section(pdf, "Рекомендации")
        for i, rec in enumerate(recommendations, 1):
            _font(pdf, "Sans", "", 10, t["body"])
            h = _mc_height(pdf, W - 18, 5, rec)
            card_h = h + 9
            _need(pdf, card_h + 4)
            y = pdf.get_y()
            _box(pdf, M, y, W, card_h, t["panel2"], t["border"])
            pdf.set_fill_color(*t["accent"])
            pdf.rect(M, y, 1.2, card_h, style="F")

            pdf.set_xy(M + 6, y + 4.5)
            _font(pdf, "Mono", "B", 10.5, t["accent"])
            pdf.cell(8, 5, str(i))

            _font(pdf, "Sans", "", 10, t["body"])
            _mc(pdf, M + 16, y + 4.5, W - 22, 5, rec)
            pdf.set_y(y + card_h + 3.5)

    # ============================
    # ПРИМЕЧАНИЕ
    # ============================
    _need(pdf, 24)
    pdf.set_y(pdf.get_y() + 6)
    _font(pdf, "Sans", "", 8, t["muted"])
    _mc(pdf, M, pdf.get_y(), W, 4,
        "Отчёт сформирован автоматически на основе ответов пользователя. "
        "Оценки финансовых потерь ориентировочные. "
        "Для точного BIA требуется анализ внутренних процессов компании.")

    return bytes(pdf.output())
