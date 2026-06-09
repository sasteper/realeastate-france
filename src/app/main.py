"""
IAD France — Property Price Estimator GUI.

Flet 0.85 compatible. Barbie theme edition.

Author: [Twoje Imię i Nazwisko]
License: MIT
"""

import logging
import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

HEADER_GIF = Path(__file__).parent / "header_anim.gif"

from db.database import DatabaseManager
from model.predictor import DPE_CLASSES, Predictor
from utils.validators import validate_bedrooms, validate_image_count, validate_surface
from model.similar import SimilarListingsFinder

# ── Logging ───────────────────────────────────────────────────────────────────
(ROOT / "data").mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(ROOT / "data" / "app.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

# ── Barbie Design tokens ───────────────────────────────────────────────────────
C_BG      = "#0D1B2A"      # bardzo ciemny róż / fiolet
C_SURFACE = "#112236"      # ciemny róż
C_CARD    = "#162C42"      # karta
C_ACCENT  = "#89CFF0"      # barbie pink
C_ACCENT2 = "#FFB6C1"      # hot pink
C_GOLD    = "#FFB6C1"      # złoty akcent
C_TEXT    = "#E8F4FD"      # jasny róż/biały
C_MUTED   = "#7BAFC8"      # wyciszony róż
C_BORDER  = "#1E4060"      # bordura
C_INPUT   = "#0F2535"      # input bg
C_GREEN   = "#89CFF0"      # "dobra" cena = hot pink
C_YELLOW  = "#FFB6C1"      # "średnia" = złoty
C_RED     = "#FF8FAB"      # "za wysoka" = barbie

DPE_COLORS = {
    "A": "#2ECC71", "B": "#27AE60", "C": "#F1C40F",
    "D": "#E67E22", "E": "#E74C3C", "F": "#C0392B", "G": "#8E44AD",
}

PROPERTY_LABELS = {
    "apartment": "🏢 Mieszkanie",
    "house":     "🏡 Dom",
    "land":      "🌿 Działka",
}

LABEL_COLORS = {
    "Okazyjna 🟢":   "#2ECC71",
    "Przeciętna 🟡": C_GOLD,
    "Za wysoka 🔴":  C_ACCENT,
}


def P(left=0, top=0, right=0, bottom=0):
    """Shortcut for ft.Padding."""
    return ft.Padding(left=left, top=top, right=right, bottom=bottom)


def Psym(h=0, v=0):
    """Symmetric padding."""
    return ft.Padding(left=h, right=h, top=v, bottom=v)


def border_all(w, color):
    """Full border helper."""
    s = ft.BorderSide(width=w, color=color)
    return ft.Border(left=s, top=s, right=s, bottom=s)


def fmt_eur(value: float) -> str:
    """Format as EUR."""
    return f"{int(value):,} EUR".replace(",", " ")


def card(content, padding=20):
    """Barbie card."""
    return ft.Container(
        content=content,
        bgcolor=C_CARD,
        border_radius=20,
        padding=padding,
        border=border_all(1, C_BORDER),
    )


def sec_title(text, icon=""):
    """Section heading."""
    children = []
    if icon:
        children.append(ft.Text(icon, size=18))
    children.append(
        ft.Text(text, size=16, weight=ft.FontWeight.BOLD, color=C_ACCENT2)
    )
    return ft.Row(children, spacing=8)


class PropertyEstimatorApp:
    """
    Barbie-themed IAD France property price estimator.

    Args:
        page: Flet Page instance.
    """

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.predictor = Predictor(ROOT / "models")
        self.db = DatabaseManager(ROOT / "data" / "history.db")
        self.db.log_action("STARTUP", "App started — Pastel edition")
        self.finder = SimilarListingsFinder(ROOT / "data" / "iad_clean.csv")
        self._setup_page()
        self._init_state()
        self._build_ui()

    def _setup_page(self):
        self.page.title = "🩷 IAD France — Estymator Cen"
        self.page.bgcolor = C_BG
        self.page.padding = 0
        self.page.window.width = 1100
        self.page.window.height = 860
        self.page.window.min_width = 820

    def _init_state(self):
        self._selected_dpe  = "D"
        self._selected_type = "apartment"
        self._amenities = {
            "has_pool": False, "has_terrace": False, "has_view": False,
            "has_garden": False, "has_transport": False, "is_quiet": False,
            "has_fireplace": False, "needs_work": False,
        }
        self._dpe_btns     = {}
        self._type_btns    = {}
        self._amenity_chips = {}

        # Direct column references (no Ref needed)
        self._hist_col = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=10, expand=True)
        self._logs_col    = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=6,  expand=True)
        self._similar_col = ft.Column(spacing=10, visible=False)

        # Error text & result card — direct refs
        self._error_text  = ft.Text("", color=C_ACCENT, size=13, visible=False)
        self._res_card    = ft.Container(visible=False)

        # Result texts
        self._ols_price = ft.Text("—", size=26, weight=ft.FontWeight.BOLD, color=C_ACCENT)
        self._ols_pi    = ft.Text("", size=11, color=C_MUTED)
        self._ols_lbl   = ft.Text("", size=13, weight=ft.FontWeight.BOLD)
        self._rf_price  = ft.Text("—", size=26, weight=ft.FontWeight.BOLD, color=C_ACCENT2)
        self._rf_pi     = ft.Text("", size=11, color=C_MUTED)
        self._rf_lbl    = ft.Text("", size=13, weight=ft.FontWeight.BOLD)

        # Input fields
        self._f_surface  = ft.TextField(
            hint_text="np. 85", hint_style=ft.TextStyle(color=C_MUTED),
            text_style=ft.TextStyle(color=C_TEXT, size=15),
            bgcolor=C_INPUT, border_color=C_BORDER,
            focused_border_color=C_ACCENT, border_radius=12, height=48,
            content_padding=Psym(h=14, v=0),
            input_filter=ft.InputFilter(regex_string=r"[0-9\.]"), width=160,
        )
        self._f_bedrooms = ft.TextField(
            hint_text="np. 3", hint_style=ft.TextStyle(color=C_MUTED),
            text_style=ft.TextStyle(color=C_TEXT, size=15),
            bgcolor=C_INPUT, border_color=C_BORDER,
            focused_border_color=C_ACCENT, border_radius=12, height=48,
            content_padding=Psym(h=14, v=0),
            input_filter=ft.InputFilter(regex_string=r"[0-9]"), width=120,
        )
        self._f_images   = ft.TextField(
            hint_text="np. 10", hint_style=ft.TextStyle(color=C_MUTED),
            text_style=ft.TextStyle(color=C_TEXT, size=15),
            bgcolor=C_INPUT, border_color=C_BORDER,
            focused_border_color=C_ACCENT, border_radius=12, height=48,
            content_padding=Psym(h=14, v=0),
            input_filter=ft.InputFilter(regex_string=r"[0-9]"), width=120,
        )

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._content = ft.Container(
            content=self._build_estimator_tab(),
            expand=True,
            padding=P(left=0, top=24, right=24, bottom=24),
        )

        rail = ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            bgcolor=C_SURFACE,
            indicator_color=C_ACCENT,
            leading=ft.Container(
                content=ft.Column([
                    ft.Text("🩵", size=30),
                    ft.Text("IAD", size=13, weight=ft.FontWeight.BOLD, color=C_ACCENT),
                    ft.Text("Pastel", size=10, color=C_MUTED),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=2),
                padding=Psym(v=16),
            ),
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icon(ft.Icons.CALCULATE_OUTLINED, color=C_MUTED),
                    selected_icon=ft.Icon(ft.Icons.CALCULATE, color=C_TEXT),
                    label="Estymator",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icon(ft.Icons.HISTORY_OUTLINED, color=C_MUTED),
                    selected_icon=ft.Icon(ft.Icons.HISTORY, color=C_TEXT),
                    label="Historia",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icon(ft.Icons.TERMINAL_OUTLINED, color=C_MUTED),
                    selected_icon=ft.Icon(ft.Icons.TERMINAL, color=C_TEXT),
                    label="Logi",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icon(ft.Icons.INFO_OUTLINE, color=C_MUTED),
                    selected_icon=ft.Icon(ft.Icons.INFO, color=C_TEXT),
                    label="O modelu",
                ),
            ],
            on_change=self._on_nav,
            min_width=80,
        )

        self.page.add(ft.Row(
            [rail, ft.VerticalDivider(width=1, color=C_BORDER), self._content],
            expand=True, spacing=0,
        ))

    def _on_nav(self, e):
        idx = e.control.selected_index
        if idx == 0:
            self._content.content = self._build_estimator_tab()
        elif idx == 1:
            self._refresh_history()
            self._content.content = self._build_history_tab()
        elif idx == 2:
            self._refresh_logs()
            self._content.content = self._build_logs_tab()
        elif idx == 3:
            self._content.content = self._build_about_tab()
        self._content.update()

    # ── DPE buttons ───────────────────────────────────────────────────────────

    def _build_dpe_row(self):
        self._dpe_btns = {}
        btns = []
        for cls in DPE_CLASSES:
            color = DPE_COLORS[cls]
            is_sel = cls == self._selected_dpe
            c = ft.Container(
                content=ft.Text(cls, size=14, weight=ft.FontWeight.BOLD,
                                color=C_TEXT if is_sel else C_MUTED),
                bgcolor=color if is_sel else C_INPUT,
                border_radius=8,
                padding=Psym(h=14, v=10),
                border=border_all(2 if is_sel else 1, color if is_sel else C_BORDER),
                on_click=lambda e, c=cls: self._select_dpe(c),
            )
            self._dpe_btns[cls] = c
            btns.append(c)
        return ft.Row(btns, spacing=8)

    def _select_dpe(self, cls):
        self._selected_dpe = cls
        for c, btn in self._dpe_btns.items():
            color = DPE_COLORS[c]
            is_sel = c == cls
            btn.bgcolor = color if is_sel else C_INPUT
            btn.border  = border_all(2 if is_sel else 1, color if is_sel else C_BORDER)
            btn.content.color = C_TEXT if is_sel else C_MUTED
            btn.update()

    # ── Type buttons ──────────────────────────────────────────────────────────

    def _build_type_row(self):
        self._type_btns = {}
        btns = []
        for ptype, plabel in PROPERTY_LABELS.items():
            is_sel = ptype == self._selected_type
            c = ft.Container(
                content=ft.Text(plabel, size=13,
                                color=C_TEXT if is_sel else C_MUTED),
                bgcolor=C_ACCENT if is_sel else C_INPUT,
                border_radius=12,
                padding=Psym(h=16, v=12),
                border=border_all(2 if is_sel else 1, C_ACCENT if is_sel else C_BORDER),
                on_click=lambda e, t=ptype: self._select_type(t),
            )
            self._type_btns[ptype] = c
            btns.append(c)
        return ft.Row(btns, spacing=10)

    def _select_type(self, ptype):
        self._selected_type = ptype
        for t, btn in self._type_btns.items():
            is_sel = t == ptype
            btn.bgcolor = C_ACCENT if is_sel else C_INPUT
            btn.border  = border_all(2 if is_sel else 1, C_ACCENT if is_sel else C_BORDER)
            btn.content.color = C_TEXT if is_sel else C_MUTED
            btn.update()

    # ── Amenity chips ─────────────────────────────────────────────────────────

    def _build_amenity_chips(self):
        LABELS = {
            "has_pool":      "🏊 Basen",
            "has_terrace":   "☀️ Taras",
            "has_view":      "🌅 Widok",
            "has_garden":    "🌳 Ogród",
            "has_transport": "🚌 Komunikacja",
            "is_quiet":      "🔇 Cisza",
            "has_fireplace": "🔥 Kominek",
            "needs_work":    "🔨 Remont",
        }
        self._amenity_chips = {}
        chips = []
        for key, label in LABELS.items():
            is_active = self._amenities[key]
            chip = ft.Container(
                content=ft.Text(label, size=13,
                                color=C_TEXT if is_active else C_MUTED),
                bgcolor=C_ACCENT if is_active else C_INPUT,
                border_radius=20,
                padding=Psym(h=14, v=8),
                border=border_all(1.5, C_ACCENT if is_active else C_BORDER),
                on_click=lambda e, k=key: self._toggle_amenity(k),
            )
            self._amenity_chips[key] = chip
            chips.append(chip)
        return chips

    def _toggle_amenity(self, key):
        self._amenities[key] = not self._amenities[key]
        chip = self._amenity_chips[key]
        is_active = self._amenities[key]
        chip.bgcolor = C_ACCENT if is_active else C_INPUT
        chip.border  = border_all(1.5, C_ACCENT if is_active else C_BORDER)
        chip.content.color = C_TEXT if is_active else C_MUTED
        chip.update()

    def _field_col(self, label, field):
        return ft.Column([
            ft.Text(label, size=12, color=C_MUTED),
            field,
        ], spacing=4, tight=True)

    # ── Result card ───────────────────────────────────────────────────────────

    def _result_box(self, price_txt, pi_txt, lbl_txt, model_name, accent):
        return ft.Container(
            content=ft.Column([
                ft.Text(model_name, size=11, color=C_MUTED),
                price_txt,
                pi_txt,
                lbl_txt,
            ], spacing=4, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=C_SURFACE,
            border_radius=16,
            padding=Psym(h=24, v=16),
            border=border_all(2, accent),
            expand=True,
            alignment=ft.Alignment(0, 0),
        )

    # ── Estimator tab ─────────────────────────────────────────────────────────

    def _build_estimator_tab(self):
        self._res_card.content = ft.Column([
            ft.Divider(height=1, color=C_BORDER),
            ft.Text("🩵 Wyniki estymacji", size=16,
                    weight=ft.FontWeight.BOLD, color=C_ACCENT2),
            ft.Row([
                self._result_box(self._ols_price, self._ols_pi,
                                 self._ols_lbl, "OLS — Regresja liniowa", C_ACCENT),
                self._result_box(self._rf_price, self._rf_pi,
                                 self._rf_lbl, "Random Forest", C_ACCENT2),
            ], spacing=16),
        ], spacing=12)

        calc_btn = ft.Container(
            content=ft.Text("🔍  Oblicz cenę", size=15, color=C_TEXT,
                            weight=ft.FontWeight.BOLD),
            bgcolor=C_ACCENT,
            border_radius=30,
            padding=Psym(h=40, v=14),
            on_click=self._on_calculate,
        )

        return ft.Column([
            ft.Text("Estymator ceny nieruchomości 🩵",
                    size=22, weight=ft.FontWeight.BOLD, color=C_ACCENT),
            ft.Text("Wypełnij parametry i kliknij Oblicz cenę",
                    size=13, color=C_MUTED),
            ft.Divider(height=1, color=C_BORDER),
            self._error_text,

            card(ft.Column([
                sec_title("Podstawowe parametry", "📐"),
                ft.Divider(height=1, color=C_BORDER),
                ft.Row([
                    self._field_col("Powierzchnia (m²)", self._f_surface),
                    self._field_col("Sypialnie", self._f_bedrooms),
                    self._field_col("Liczba zdjęć", self._f_images),
                ], spacing=16),
            ], spacing=12)),

            ft.Row([
                card(ft.Column([
                    sec_title("Klasa energetyczna DPE", "⚡"),
                    ft.Divider(height=1, color=C_BORDER),
                    self._build_dpe_row(),
                ], spacing=12)),
                card(ft.Column([
                    sec_title("Typ nieruchomości", "🏠"),
                    ft.Divider(height=1, color=C_BORDER),
                    self._build_type_row(),
                ], spacing=12)),
            ], spacing=16),

            card(ft.Column([
                sec_title("Udogodnienia i cechy", "✨"),
                ft.Divider(height=1, color=C_BORDER),
                ft.Row(self._build_amenity_chips(),
                       wrap=True, spacing=10, run_spacing=10),
            ], spacing=12)),

            ft.Row([calc_btn], alignment=ft.MainAxisAlignment.CENTER),
            self._res_card,
            self._similar_col,
            ft.Row([
                ft.Image(
                    src=str(HEADER_GIF),
                    fit=ft.BoxFit.CONTAIN,
                    repeat=ft.ImageRepeat.NO_REPEAT,
                    width=600,
                    height=140,
                ),
            ], alignment=ft.MainAxisAlignment.CENTER),
        ], scroll=ft.ScrollMode.AUTO, spacing=16, expand=True)

    # ── Calculate ─────────────────────────────────────────────────────────────

    def _on_calculate(self, e):
        errors = []
        ok_s, surface,  msg_s = validate_surface(self._f_surface.value or "")
        ok_b, bedrooms, msg_b = validate_bedrooms(self._f_bedrooms.value or "")
        ok_i, images,   msg_i = validate_image_count(self._f_images.value or "")

        for ok, field, msg in [
            (ok_s, self._f_surface,  msg_s),
            (ok_b, self._f_bedrooms, msg_b),
            (ok_i, self._f_images,   msg_i),
        ]:
            field.border_color = C_BORDER if ok else C_ACCENT
            field.update()
            if not ok:
                errors.append(msg)

        if errors:
            self._error_text.value   = " | ".join(errors)
            self._error_text.visible = True
            self._error_text.update()
            return

        self._error_text.visible = False
        self._error_text.update()

        amenities = {k: int(v) for k, v in self._amenities.items()}
        try:
            ols_r, rf_r = self.predictor.predict_both(
                surface_m2=surface, bedrooms=bedrooms,
                dpe_class=self._selected_dpe, image_count=images,
                property_type=self._selected_type, amenities=amenities,
            )
        except Exception as exc:
            logger.exception("Prediction error")
            self._error_text.value   = f"Błąd: {exc}"
            self._error_text.visible = True
            self._error_text.update()
            return

        for price_t, pi_t, lbl_t, res in [
            (self._ols_price, self._ols_pi, self._ols_lbl, ols_r),
            (self._rf_price,  self._rf_pi,  self._rf_lbl,  rf_r),
        ]:
            price_t.value = fmt_eur(res.price_estimate)
            pi_t.value    = f"95% PI: {fmt_eur(res.price_low)} — {fmt_eur(res.price_high)}"
            lbl_t.value   = res.valuation_label
            lbl_t.color   = LABEL_COLORS.get(res.valuation_label, C_TEXT)
            price_t.update(); pi_t.update(); lbl_t.update()

        self._res_card.visible = True
        self._res_card.update()

        for res in [ols_r, rf_r]:
            self.db.save_estimation(
                surface_m2=surface, bedrooms=bedrooms,
                dpe_class=self._selected_dpe, image_count=images,
                property_type=self._selected_type, amenities=amenities,
                model_used=res.model_name,
                price_estimate=res.price_estimate,
                price_low=res.price_low, price_high=res.price_high,
                valuation_label=res.valuation_label,
            )

        # Show similar listings
        self._show_similar(surface, bedrooms, ols_r.price_estimate)


    def _show_similar(self, surface: float, bedrooms: int, price: float) -> None:
        """
        Find and display similar listings from the dataset.

        Args:
            surface: Surface area in m².
            bedrooms: Number of bedrooms.
            price: Reference price estimate in EUR.
        """
        listings = self.finder.find(
            surface_m2=surface,
            bedrooms=bedrooms,
            property_type=self._selected_type,
            price_estimate=price,
            n=5,
        )

        self._similar_col.controls.clear()
        self._similar_col.controls.append(
            ft.Column([
                ft.Divider(height=1, color=C_BORDER),
                sec_title("Podobne oferty z bazy IAD France", "🔎"),
            ], spacing=8)
        )

        DPE_COLORS_LOCAL = {
            "A": "#2ECC71", "B": "#27AE60", "C": "#F1C40F",
            "D": "#E67E22", "E": "#E74C3C", "F": "#C0392B", "G": "#8E44AD",
        }

        for lst in listings:
            dpe_color = DPE_COLORS_LOCAL.get(lst.dpe_class, C_MUTED)
            sim_color = (
                "#2ECC71" if lst.similarity_pct >= 90
                else C_ACCENT2 if lst.similarity_pct >= 70
                else C_MUTED
            )

            self._similar_col.controls.append(
                ft.Container(
                    content=ft.Row([
                        # Similarity badge
                        ft.Container(
                            content=ft.Column([
                                ft.Text(f"{lst.similarity_pct}%", size=14,
                                        weight=ft.FontWeight.BOLD, color=sim_color),
                                ft.Text("zgodność", size=9, color=C_MUTED),
                            ], horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                               spacing=2),
                            width=60, alignment=ft.Alignment(0, 0),
                        ),
                        ft.VerticalDivider(width=1, color=C_BORDER),
                        # Main info
                        ft.Column([
                            ft.Text(
                                lst.title if lst.title else "Oferta IAD France",
                                size=12, color=C_TEXT,
                                overflow=ft.TextOverflow.ELLIPSIS,
                                max_lines=1,
                            ),
                            ft.Row([
                                ft.Text(f"📍 {lst.city}", size=11, color=C_MUTED),
                                ft.Text(f"📐 {lst.surface_m2:.0f} m²", size=11, color=C_MUTED),
                                ft.Text(f"🛏 {int(lst.bedrooms)}", size=11, color=C_MUTED),
                                ft.Container(
                                    ft.Text(lst.dpe_class, size=10,
                                            weight=ft.FontWeight.BOLD, color=C_TEXT),
                                    bgcolor=dpe_color, border_radius=4,
                                    padding=Psym(h=6, v=2),
                                ),
                            ], spacing=12),
                        ], expand=True, spacing=4),
                        # Price
                        ft.Column([
                            ft.Text(fmt_eur(lst.price), size=15,
                                    weight=ft.FontWeight.BOLD, color=C_ACCENT),
                            ft.Text(f"{lst.price_per_m2:,.0f} EUR/m²",
                                    size=11, color=C_MUTED),
                        ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=2),
                    ], spacing=12, vertical_alignment=ft.CrossAxisAlignment.CENTER),
                    bgcolor=C_CARD,
                    border_radius=14,
                    padding=Psym(h=16, v=12),
                    border=border_all(1, C_BORDER),
                    on_click=lambda e, url=lst.url: self._open_url(url) if url else None,
                )
            )

        self._similar_col.visible = True
        self._similar_col.update()

    def _open_url(self, url: str) -> None:
        """Open listing URL in default browser."""
        import webbrowser
        if url:
            webbrowser.open(url)

    # ── History tab ───────────────────────────────────────────────────────────

    def _build_history_tab(self):
        clear_btn = ft.Container(
            content=ft.Text("🗑  Wyczyść", size=13, color=C_ACCENT),
            bgcolor=C_CARD, border_radius=10,
            padding=Psym(h=16, v=8),
            border=border_all(1, C_ACCENT),
            on_click=self._on_clear_history,
        )
        return ft.Column([
            ft.Row([
                ft.Column([
                    ft.Text("Historia oszacowań 🩵", size=22,
                            weight=ft.FontWeight.BOLD, color=C_ACCENT),
                    ft.Text("Wyniki zapisane w lokalnej bazie SQLite",
                            size=13, color=C_MUTED),
                ], expand=True),
                clear_btn,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=1, color=C_BORDER),
            self._hist_col,
        ], spacing=16, expand=True)

    def _refresh_history(self):
        rows = self.db.get_history(100)
        self._hist_col.controls.clear()
        if not rows:
            self._hist_col.controls.append(
                ft.Text("Brak wyników.", color=C_MUTED, size=14))
        else:
            for r in rows:
                lc = LABEL_COLORS.get(r.get("valuation_label", ""), C_TEXT)
                self._hist_col.controls.append(
                    card(ft.Row([
                        ft.Column([
                            ft.Text(f"{r['timestamp']}  •  {r['model_used']}",
                                    size=11, color=C_MUTED),
                            ft.Text(
                                f"{PROPERTY_LABELS.get(r['property_type'], r['property_type'])}"
                                f"  •  {r['surface_m2']:.0f} m²"
                                f"  •  {r['bedrooms']} sypialnie"
                                f"  •  DPE {r['dpe_class']}",
                                size=13, color=C_TEXT),
                        ], expand=True, spacing=3),
                        ft.Column([
                            ft.Text(fmt_eur(r["price_estimate"]), size=18,
                                    weight=ft.FontWeight.BOLD, color=C_ACCENT),
                            ft.Text(f"{fmt_eur(r['price_low'])} — {fmt_eur(r['price_high'])}",
                                    size=11, color=C_MUTED),
                            ft.Text(r.get("valuation_label", ""), size=12,
                                    color=lc, weight=ft.FontWeight.BOLD),
                        ], horizontal_alignment=ft.CrossAxisAlignment.END, spacing=3),
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), padding=14)
                )

    def _on_clear_history(self, e):
        deleted = self.db.clear_history()
        self._refresh_history()
        self._hist_col.update()
        sb = ft.SnackBar(
            content=ft.Text(f"Usunięto {deleted} rekordów. 🩵", color=C_TEXT),
            bgcolor=C_CARD, open=True,
        )
        self.page.overlay.append(sb)
        self.page.update()

    # ── Logs tab ──────────────────────────────────────────────────────────────

    def _build_logs_tab(self):
        return ft.Column([
            ft.Text("Logi aplikacji 🔍", size=22,
                    weight=ft.FontWeight.BOLD, color=C_ACCENT),
            ft.Text("Wewnętrzne zdarzenia aplikacji", size=13, color=C_MUTED),
            ft.Divider(height=1, color=C_BORDER),
            self._logs_col,
        ], spacing=16, expand=True)

    def _refresh_logs(self):
        logs = self.db.get_logs(150)
        self._logs_col.controls.clear()
        level_colors = {"INFO": C_ACCENT2, "WARNING": C_GOLD, "ERROR": C_ACCENT}
        if not logs:
            self._logs_col.controls.append(
                ft.Text("Brak logów.", color=C_MUTED, size=14))
        else:
            for lg in logs:
                color = level_colors.get(lg.get("level", "INFO"), C_MUTED)
                self._logs_col.controls.append(ft.Container(
                    content=ft.Row([
                        ft.Text(lg["timestamp"], size=11, color=C_MUTED, width=155),
                        ft.Container(
                            ft.Text(lg.get("level", ""), size=10, color=color,
                                    weight=ft.FontWeight.BOLD),
                            bgcolor=C_SURFACE, border_radius=4,
                            padding=Psym(h=6, v=2),
                            border=border_all(1, color), width=65,
                        ),
                        ft.Text(f"[{lg['action']}]", size=11, color=C_ACCENT,
                                weight=ft.FontWeight.BOLD),
                        ft.Text(lg.get("details", ""), size=11, color=C_TEXT,
                                overflow=ft.TextOverflow.ELLIPSIS, expand=True),
                    ], spacing=10),
                    bgcolor=C_CARD, border_radius=8, padding=Psym(h=12, v=6),
                ))

    # ── About tab ─────────────────────────────────────────────────────────────

    def _build_about_tab(self):
        m = self.predictor.model_metrics

        def row(label, val):
            return ft.Row([
                ft.Text(label, size=13, color=C_MUTED, expand=True),
                ft.Text(str(val), size=13, color=C_ACCENT2,
                        weight=ft.FontWeight.BOLD),
            ])

        return ft.Column([
            ft.Text("O modelu 🩵", size=22, weight=ft.FontWeight.BOLD, color=C_ACCENT),
            ft.Divider(height=1, color=C_BORDER),
            ft.Row([
                card(ft.Column([
                    sec_title("Metryki (zbiór testowy)", "📈"),
                    ft.Divider(height=1, color=C_BORDER),
                    row("OLS R² (test)", f"{m['OLS R² (test)']:.4f}"),
                    row("RF  R² (test)", f"{m['RF  R² (test)']:.4f}"),
                    row("Próbka treningowa", m["Train size"]),
                    row("Próbka testowa",    m["Test size"]),
                ], spacing=10), padding=20),
                card(ft.Column([
                    sec_title("Legenda wyceny", "🏷️"),
                    ft.Divider(height=1, color=C_BORDER),
                    ft.Row([ft.Container(width=12, height=12, bgcolor="#2ECC71", border_radius=6),
                            ft.Text("Okazyjna  ≤ 160 000 EUR", size=13, color=C_TEXT)], spacing=8),
                    ft.Row([ft.Container(width=12, height=12, bgcolor=C_GOLD, border_radius=6),
                            ft.Text("Przeciętna  160 – 371k EUR", size=13, color=C_TEXT)], spacing=8),
                    ft.Row([ft.Container(width=12, height=12, bgcolor=C_ACCENT, border_radius=6),
                            ft.Text("Za wysoka  > 371 000 EUR", size=13, color=C_TEXT)], spacing=8),
                ], spacing=10), padding=20),
            ], spacing=16),
            card(ft.Column([
                sec_title("Zmienne modelu OLS", "📋"),
                ft.Divider(height=1, color=C_BORDER),
                ft.Row([
                    ft.Column([
                        ft.Text("• log(powierzchnia)", size=12, color=C_TEXT),
                        ft.Text("• Liczba sypialni", size=12, color=C_TEXT),
                        ft.Text("• Klasa DPE (A=1 … G=7)", size=12, color=C_TEXT),
                        ft.Text("• Liczba zdjęć ogłoszenia", size=12, color=C_TEXT),
                    ]),
                    ft.Column([
                        ft.Text("• Basen, taras, widok, ogród", size=12, color=C_TEXT),
                        ft.Text("• Komunikacja, cisza, kominek", size=12, color=C_TEXT),
                        ft.Text("• Wymaga remontu (ujemny)", size=12, color=C_TEXT),
                        ft.Text("• Typ: mieszkanie / działka", size=12, color=C_TEXT),
                    ]),
                ], spacing=40),
            ], spacing=10), padding=20),
        ], scroll=ft.ScrollMode.AUTO, spacing=16, expand=True)


def main(page: ft.Page) -> None:
    """
    Entry point for the Flet application.

    Args:
        page: Flet page injected by the framework.
    """
    PropertyEstimatorApp(page)


if __name__ == "__main__":
    ft.app(target=main)
