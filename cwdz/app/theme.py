"""应用全局主题与样式。"""

from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

THEME_SETTING_KEY = "ui/theme"
DEFAULT_THEME = "apple"

LEGACY_THEME_MAP = {
    "light": "apple",
    "dark": "apple_dark",
    "frost": "apple",
    "cyber": "apple_dark",
    "warm": "aurora",
    "ledger": "midnight",
}

THEMES: dict[str, dict[str, str]] = {
    "apple": {
        "label": "苹果浅色",
        "bg": "#f5f5f7",
        "text": "#1d1d1f",
        "text_secondary": "#86868b",
        "text_body": "#3a3a3c",
        "header_bg": "#ffffff",
        "header_border": "#d1d1d6",
        "card_bg": "#ffffff",
        "card_border": "#d1d1d6",
        "card_accent": "#007aff",
        "tab_bg": "#e8e8ed",
        "tab_text": "#86868b",
        "tab_selected_bg": "#ffffff",
        "tab_selected_text": "#1d1d1f",
        "tab_hover": "#f2f2f7",
        "tab_indicator": "#007aff",
        "sidebar_bg": "#e8e8ed",
        "content_panel_bg": "#ffffff",
        "grouped_bg": "#ffffff",
        "segment_track": "#e8e8ed",
        "input_bg": "#ffffff",
        "input_border": "#c7c7cc",
        "input_focus_border": "#007aff",
        "input_focus_bg": "#ffffff",
        "btn_bg": "#ffffff",
        "btn_text": "#1d1d1f",
        "btn_border": "#c7c7cc",
        "btn_hover_bg": "#f2f2f7",
        "btn_hover_border": "#aeaeb2",
        "btn_disabled_text": "#aeaeb2",
        "btn_disabled_bg": "#f2f2f7",
        "primary": "#007aff",
        "primary_hover": "#0071e3",
        "primary_pressed": "#0060df",
        "primary_disabled": "#99caff",
        "primary_text": "#ffffff",
        "ghost_text": "#007aff",
        "ghost_hover_bg": "#e8f2ff",
        "ghost_hover_border": "#cce4ff",
        "badge_bg": "#e8f2ff",
        "badge_text": "#004999",
        "badge_border": "#99caff",
        "status_ok": "#34c759",
        "accent": "#007aff",
        "qr_placeholder_bg": "#f2f2f7",
        "qr_placeholder_border": "#c7c7cc",
        "qr_placeholder_text": "#86868b",
        "qr_image_bg": "#ffffff",
        "qr_image_border": "#007aff",
        "log_bg": "#1c1c1e",
        "log_border": "#3a3a3c",
        "log_text": "#a1a1a6",
        "selection": "#cce4ff",
    },
    "apple_dark": {
        "label": "苹果深色",
        "bg": "#1c1c1e",
        "text": "#f5f5f7",
        "text_secondary": "#98989d",
        "text_body": "#ebebf0",
        "header_bg": "#2c2c2e",
        "header_border": "#3a3a3c",
        "card_bg": "#2c2c2e",
        "card_border": "#3a3a3c",
        "card_accent": "#0a84ff",
        "tab_bg": "#2c2c2e",
        "tab_text": "#98989d",
        "tab_selected_bg": "#0a84ff",
        "tab_selected_text": "#ffffff",
        "tab_hover": "#3a3a3c",
        "tab_indicator": "#0a84ff",
        "sidebar_bg": "#2c2c2e",
        "content_panel_bg": "#2c2c2e",
        "grouped_bg": "#3a3a3c",
        "segment_track": "#3a3a3c",
        "input_bg": "#1c1c1e",
        "input_border": "#48484a",
        "input_focus_border": "#0a84ff",
        "input_focus_bg": "#2c2c2e",
        "btn_bg": "#3a3a3c",
        "btn_text": "#f5f5f7",
        "btn_border": "#48484a",
        "btn_hover_bg": "#48484a",
        "btn_hover_border": "#636366",
        "btn_disabled_text": "#636366",
        "btn_disabled_bg": "#2c2c2e",
        "primary": "#0a84ff",
        "primary_hover": "#409cff",
        "primary_pressed": "#0066cc",
        "primary_disabled": "#1e3a5f",
        "primary_text": "#ffffff",
        "ghost_text": "#409cff",
        "ghost_hover_bg": "#1a2a3d",
        "ghost_hover_border": "#0a84ff",
        "badge_bg": "#1a2a3d",
        "badge_text": "#99caff",
        "badge_border": "#0a84ff",
        "status_ok": "#30d158",
        "accent": "#0a84ff",
        "qr_placeholder_bg": "#1c1c1e",
        "qr_placeholder_border": "#48484a",
        "qr_placeholder_text": "#98989d",
        "qr_image_bg": "#2c2c2e",
        "qr_image_border": "#0a84ff",
        "log_bg": "#000000",
        "log_border": "#3a3a3c",
        "log_text": "#98989d",
        "selection": "#0a84ff",
    },
    "cyber": {
        "label": "赛博科技",
        "bg": "#070b14",
        "text": "#f1f5f9",
        "text_secondary": "#7dd3fc",
        "text_body": "#cbd5e1",
        "header_bg": "#0b1220",
        "header_border": "#1e3a5f",
        "card_bg": "#0f172a",
        "card_border": "#1e293b",
        "card_accent": "#22d3ee",
        "tab_bg": "#0b1220",
        "tab_text": "#64748b",
        "tab_selected_bg": "#111827",
        "tab_selected_text": "#e0f2fe",
        "tab_hover": "#131c2e",
        "tab_indicator": "#22d3ee",
        "input_bg": "#0a101c",
        "input_border": "#243044",
        "input_focus_border": "#22d3ee",
        "input_focus_bg": "#0f172a",
        "btn_bg": "#111827",
        "btn_text": "#e2e8f0",
        "btn_border": "#334155",
        "btn_hover_bg": "#1e293b",
        "btn_hover_border": "#475569",
        "btn_disabled_text": "#475569",
        "btn_disabled_bg": "#0f172a",
        "primary": "#0891b2",
        "primary_hover": "#06b6d4",
        "primary_pressed": "#0e7490",
        "primary_disabled": "#164e63",
        "primary_text": "#ecfeff",
        "ghost_text": "#67e8f9",
        "ghost_hover_bg": "#083344",
        "ghost_hover_border": "#155e75",
        "badge_bg": "#082f49",
        "badge_text": "#a5f3fc",
        "badge_border": "#155e75",
        "status_ok": "#34d399",
        "accent": "#22d3ee",
        "qr_placeholder_bg": "#0a101c",
        "qr_placeholder_border": "#334155",
        "qr_placeholder_text": "#64748b",
        "qr_image_bg": "#111827",
        "qr_image_border": "#22d3ee",
        "log_bg": "#020617",
        "log_border": "#1e3a5f",
        "log_text": "#7dd3fc",
        "selection": "#164e63",
    },
    "aurora": {
        "label": "极光紫电",
        "bg": "#09080f",
        "text": "#f5f3ff",
        "text_secondary": "#c4b5fd",
        "text_body": "#ddd6fe",
        "header_bg": "#110d1a",
        "header_border": "#4c1d95",
        "card_bg": "#13101f",
        "card_border": "#2e1065",
        "card_accent": "#a78bfa",
        "tab_bg": "#110d1a",
        "tab_text": "#6b7280",
        "tab_selected_bg": "#1a1429",
        "tab_selected_text": "#ede9fe",
        "tab_hover": "#1f1630",
        "tab_indicator": "#8b5cf6",
        "input_bg": "#0c0a14",
        "input_border": "#3b2667",
        "input_focus_border": "#a78bfa",
        "input_focus_bg": "#13101f",
        "btn_bg": "#1a1429",
        "btn_text": "#ede9fe",
        "btn_border": "#4c1d95",
        "btn_hover_bg": "#231933",
        "btn_hover_border": "#6d28d9",
        "btn_disabled_text": "#6b7280",
        "btn_disabled_bg": "#13101f",
        "primary": "#7c3aed",
        "primary_hover": "#8b5cf6",
        "primary_pressed": "#6d28d9",
        "primary_disabled": "#4c1d95",
        "primary_text": "#faf5ff",
        "ghost_text": "#c4b5fd",
        "ghost_hover_bg": "#2e1065",
        "ghost_hover_border": "#5b21b6",
        "badge_bg": "#2e1065",
        "badge_text": "#ddd6fe",
        "badge_border": "#6d28d9",
        "status_ok": "#4ade80",
        "accent": "#a78bfa",
        "qr_placeholder_bg": "#0c0a14",
        "qr_placeholder_border": "#4c1d95",
        "qr_placeholder_text": "#7c3aed",
        "qr_image_bg": "#13101f",
        "qr_image_border": "#8b5cf6",
        "log_bg": "#050308",
        "log_border": "#4c1d95",
        "log_text": "#c4b5fd",
        "selection": "#5b21b6",
    },
    "midnight": {
        "label": "午夜碳黑",
        "bg": "#050505",
        "text": "#fafafa",
        "text_secondary": "#737373",
        "text_body": "#d4d4d4",
        "header_bg": "#0a0a0a",
        "header_border": "#262626",
        "card_bg": "#111111",
        "card_border": "#262626",
        "card_accent": "#3b82f6",
        "tab_bg": "#0a0a0a",
        "tab_text": "#525252",
        "tab_selected_bg": "#171717",
        "tab_selected_text": "#fafafa",
        "tab_hover": "#1c1c1c",
        "tab_indicator": "#3b82f6",
        "input_bg": "#0a0a0a",
        "input_border": "#333333",
        "input_focus_border": "#3b82f6",
        "input_focus_bg": "#111111",
        "btn_bg": "#171717",
        "btn_text": "#e5e5e5",
        "btn_border": "#404040",
        "btn_hover_bg": "#262626",
        "btn_hover_border": "#525252",
        "btn_disabled_text": "#525252",
        "btn_disabled_bg": "#111111",
        "primary": "#2563eb",
        "primary_hover": "#3b82f6",
        "primary_pressed": "#1d4ed8",
        "primary_disabled": "#1e3a8a",
        "primary_text": "#eff6ff",
        "ghost_text": "#60a5fa",
        "ghost_hover_bg": "#172554",
        "ghost_hover_border": "#1e40af",
        "badge_bg": "#172554",
        "badge_text": "#93c5fd",
        "badge_border": "#1e40af",
        "status_ok": "#22c55e",
        "accent": "#3b82f6",
        "qr_placeholder_bg": "#0a0a0a",
        "qr_placeholder_border": "#404040",
        "qr_placeholder_text": "#525252",
        "qr_image_bg": "#111111",
        "qr_image_border": "#3b82f6",
        "log_bg": "#000000",
        "log_border": "#262626",
        "log_text": "#a3a3a3",
        "selection": "#1e40af",
    },
    "frost": {
        "label": "冰晶简约",
        "bg": "#eef2f7",
        "text": "#0f172a",
        "text_secondary": "#64748b",
        "text_body": "#334155",
        "header_bg": "#ffffff",
        "header_border": "#dbe3ee",
        "card_bg": "#ffffff",
        "card_border": "#dbe3ee",
        "card_accent": "#0ea5e9",
        "tab_bg": "#e2e8f0",
        "tab_text": "#64748b",
        "tab_selected_bg": "#ffffff",
        "tab_selected_text": "#0f172a",
        "tab_hover": "#f1f5f9",
        "tab_indicator": "#0ea5e9",
        "input_bg": "#f8fafc",
        "input_border": "#cbd5e1",
        "input_focus_border": "#0ea5e9",
        "input_focus_bg": "#ffffff",
        "btn_bg": "#ffffff",
        "btn_text": "#334155",
        "btn_border": "#cbd5e1",
        "btn_hover_bg": "#f8fafc",
        "btn_hover_border": "#94a3b8",
        "btn_disabled_text": "#94a3b8",
        "btn_disabled_bg": "#f1f5f9",
        "primary": "#0284c7",
        "primary_hover": "#0ea5e9",
        "primary_pressed": "#0369a1",
        "primary_disabled": "#7dd3fc",
        "primary_text": "#ffffff",
        "ghost_text": "#0284c7",
        "ghost_hover_bg": "#e0f2fe",
        "ghost_hover_border": "#7dd3fc",
        "badge_bg": "#e0f2fe",
        "badge_text": "#0369a1",
        "badge_border": "#7dd3fc",
        "status_ok": "#059669",
        "accent": "#0ea5e9",
        "qr_placeholder_bg": "#f8fafc",
        "qr_placeholder_border": "#cbd5e1",
        "qr_placeholder_text": "#94a3b8",
        "qr_image_bg": "#ffffff",
        "qr_image_border": "#0ea5e9",
        "log_bg": "#0f172a",
        "log_border": "#1e293b",
        "log_text": "#7dd3fc",
        "selection": "#bae6fd",
    },
}


def theme_choices() -> list[tuple[str, str]]:
    return [(theme_id, meta["label"]) for theme_id, meta in THEMES.items()]


def normalize_theme_id(theme_id: str) -> str:
    mapped = LEGACY_THEME_MAP.get(theme_id, theme_id)
    return mapped if mapped in THEMES else DEFAULT_THEME


def load_saved_theme() -> str:
    settings = QSettings("CWDZ", "财务对账工具")
    theme_id = str(settings.value(THEME_SETTING_KEY, DEFAULT_THEME))
    return normalize_theme_id(theme_id)


def save_theme(theme_id: str) -> None:
    settings = QSettings("CWDZ", "财务对账工具")
    settings.setValue(THEME_SETTING_KEY, normalize_theme_id(theme_id))


def _theme_tokens(t: dict[str, str]) -> dict[str, str]:
    """为 QSS 提供可选键的回退值。"""
    return {
        **t,
        "sidebar_bg": t.get("sidebar_bg", t["tab_bg"]),
        "content_panel_bg": t.get("content_panel_bg", t["card_bg"]),
        "grouped_bg": t.get("grouped_bg", t["card_bg"]),
        "segment_track": t.get("segment_track", t["tab_bg"]),
    }


def build_stylesheet(theme_id: str) -> str:
    t = _theme_tokens(THEMES.get(normalize_theme_id(theme_id), THEMES[DEFAULT_THEME]))
    return f"""
QMainWindow, QWidget#CentralRoot {{
    background-color: {t["bg"]};
}}

QStackedWidget {{
    background: transparent;
    border: none;
}}

QLabel {{
    color: {t["text_body"]};
    font-size: 13px;
}}

QLabel#AppTitle {{
    color: {t["text"]};
    font-size: 24px;
    font-weight: 700;
    letter-spacing: -0.5px;
}}

QLabel#VersionBadge {{
    color: {t["text_secondary"]};
    background-color: {t["tab_bg"]};
    border: 1px solid {t["card_border"]};
    border-radius: 8px;
    padding: 4px 10px;
    font-size: 11px;
}}

QLabel#PageTitle {{
    color: {t["text"]};
    font-size: 20px;
    font-weight: 700;
}}

QLabel#PageSubtitle {{
    color: {t["text_secondary"]};
    font-size: 12px;
}}

QWidget#PageHeaderCompact QLabel#PageTitle {{
    font-size: 18px;
    font-weight: 700;
}}

QWidget#PageHeaderCompact QLabel#PageSubtitle {{
    font-size: 12px;
}}

QScrollArea {{
    border: none;
}}

QLabel#SectionTitle {{
    color: {t["text_secondary"]};
    font-size: 13px;
    font-weight: 600;
    padding: 0 0 0 16px;
}}

QLabel#SectionFooter {{
    color: {t["text_secondary"]};
    font-size: 12px;
    padding-left: 4px;
}}

QLabel#ListRowLabel {{
    color: {t["text"]};
    font-size: 14px;
    font-weight: 500;
    background: transparent;
}}

QLabel#ListRowSubtitle {{
    color: {t["text_secondary"]};
    font-size: 12px;
    background: transparent;
}}

QLabel#FieldLabel {{
    color: {t["text_secondary"]};
    font-size: 12px;
    font-weight: 500;
    background: transparent;
}}

QLabel#SidebarCaption {{
    color: {t["text_secondary"]};
    font-size: 11px;
    font-weight: 600;
    padding: 4px 8px 8px 8px;
}}

QFrame#SidebarPanel {{
    background-color: {t["sidebar_bg"]};
    border: 1px solid {t["card_border"]};
    border-radius: 12px;
}}

QFrame#SidebarStep {{
    background-color: transparent;
    border: none;
    border-radius: 8px;
}}

QFrame#SidebarStep:hover {{
    background-color: {t["tab_hover"]};
}}

QFrame#SidebarStep[selected="true"] {{
    background-color: {t["tab_indicator"]};
}}

QLabel#SidebarStepTitle {{
    color: {t["text"]};
    font-size: 13px;
    font-weight: 600;
    background: transparent;
}}

QLabel#SidebarStepDetail {{
    color: {t["text_secondary"]};
    font-size: 11px;
    background: transparent;
}}

QLabel#SidebarStepTitle[selected="true"] {{
    color: {t["primary_text"]};
}}

QLabel#SidebarStepDetail[selected="true"] {{
    color: {t["primary_text"]};
    opacity: 0.92;
}}

QFrame#ContentPanel {{
    background-color: {t["content_panel_bg"]};
    border: 1px solid {t["card_border"]};
    border-radius: 14px;
}}

QFrame#ActionBar {{
    background-color: transparent;
    border: none;
    border-top: 1px solid {t["card_border"]};
    margin-top: 0;
}}

QFrame#GroupedList {{
    background-color: {t["grouped_bg"]};
    border: 1px solid {t["card_border"]};
    border-radius: 12px;
}}

QFrame#ListRow {{
    background-color: transparent;
    border: none;
    border-bottom: 1px solid {t["card_border"]};
    min-height: 36px;
    max-height: 36px;
}}

QFrame#ListRow[lastRow="true"] {{
    border-bottom: none;
}}

QFrame#ListRow[tallRow="true"] {{
    min-height: 52px;
    max-height: 52px;
}}

QLineEdit#InlineField, QDateEdit#InlineField {{
    background-color: transparent;
    border: none;
    border-radius: 0;
    padding: 0 2px;
    min-height: 24px;
    max-height: 24px;
    color: {t["text"]};
    font-size: 15px;
}}

QLineEdit#InlineField:focus, QDateEdit#InlineField:focus {{
    color: {t["text"]};
    background-color: transparent;
    border: none;
}}

QDateEdit#InlineField::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 16px;
    border: none;
}}

QComboBox#ToolbarCombo {{
    background-color: {t["input_bg"]};
    border: 1px solid {t["input_border"]};
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 18px;
    font-size: 13px;
}}

QLineEdit#PathField {{
    background-color: transparent;
    border: none;
    border-radius: 0;
    padding: 0 4px;
    color: {t["text"]};
    font-size: 14px;
    min-height: 24px;
    max-height: 24px;
}}

QLineEdit#PathField:focus {{
    color: {t["text"]};
}}

QPushButton#CompactButton {{
    background-color: {t["btn_bg"]};
    border: 1px solid {t["btn_border"]};
    border-radius: 8px;
    padding: 4px 12px;
    font-size: 13px;
    min-height: 0;
    max-height: 24px;
}}

QFrame#HeaderBar {{
    background-color: transparent;
    border: none;
    border-radius: 0px;
}}

QFrame#Card, QFrame#LogCard {{
    background-color: {t["card_bg"]};
    border: 1px solid {t["card_border"]};
    border-top: 1px solid {t["card_border"]};
    border-radius: 12px;
}}

QLabel#AppSubtitle {{
    color: {t["text_secondary"]};
    font-size: 12px;
}}

QLabel#CardTitle {{
    color: {t["text"]};
    font-size: 14px;
    font-weight: 600;
}}

QLabel#CardHint {{
    color: {t["text_secondary"]};
    font-size: 11px;
}}

QLabel#StatusOk {{
    color: {t["status_ok"]};
    font-size: 13px;
    font-weight: 600;
}}

QLabel#StatusMuted {{
    color: {t["text_secondary"]};
    font-size: 13px;
}}

QLabel#UserBadge {{
    background-color: {t["badge_bg"]};
    color: {t["badge_text"]};
    border: 1px solid {t["badge_border"]};
    border-radius: 10px;
    padding: 10px 14px;
    font-size: 12px;
}}


QTabWidget::pane {{
    border: none;
    background: transparent;
    top: -1px;
}}

QTabBar::tab {{
    background: {t["tab_bg"]};
    color: {t["tab_text"]};
    border: 1px solid {t["card_border"]};
    border-bottom: 2px solid transparent;
    border-top-left-radius: 10px;
    border-top-right-radius: 10px;
    padding: 10px 20px;
    margin-right: 4px;
    font-size: 13px;
    min-width: 100px;
}}

QTabBar::tab:selected {{
    background: {t["tab_selected_bg"]};
    color: {t["tab_selected_text"]};
    font-weight: 600;
    border-bottom: 2px solid {t["tab_indicator"]};
}}

QTabBar::tab:hover:!selected {{
    background: {t["tab_hover"]};
    color: {t["text_body"]};
}}

QComboBox, QLineEdit, QDateEdit, QPlainTextEdit {{
    background-color: {t["input_bg"]};
    border: 1px solid {t["input_border"]};
    border-radius: 10px;
    padding: 9px 12px;
    color: {t["text"]};
    min-height: 20px;
    selection-background-color: {t["selection"]};
}}

QComboBox:focus, QLineEdit:focus, QDateEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {t["input_focus_border"]};
    background-color: {t["input_focus_bg"]};
}}

QLineEdit#InlineField, QDateEdit#InlineField, QLineEdit#PathField {{
    background-color: transparent;
    border: none;
    border-radius: 0;
    padding: 0 4px;
    min-height: 24px;
    max-height: 24px;
}}

QLineEdit#InlineField:focus, QDateEdit#InlineField:focus, QLineEdit#PathField:focus {{
    border: none;
    background-color: transparent;
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox QAbstractItemView {{
    background-color: {t["card_bg"]};
    color: {t["text"]};
    border: 1px solid {t["card_border"]};
    selection-background-color: {t["selection"]};
}}

QPushButton {{
    background-color: {t["btn_bg"]};
    color: {t["btn_text"]};
    border: 1px solid {t["btn_border"]};
    border-radius: 10px;
    padding: 9px 16px;
    font-size: 13px;
    min-height: 18px;
}}

QPushButton:hover {{
    background-color: {t["btn_hover_bg"]};
    border-color: {t["btn_hover_border"]};
}}

QPushButton:disabled {{
    color: {t["btn_disabled_text"]};
    background-color: {t["btn_disabled_bg"]};
    border-color: {t["card_border"]};
}}

QPushButton#PrimaryButton {{
    background-color: {t["primary"]};
    color: {t["primary_text"]};
    border: 1px solid {t["primary"]};
    font-weight: 600;
    padding: 5px 14px;
    font-size: 13px;
    min-height: 0;
    max-height: 28px;
    border-radius: 8px;
}}

QPushButton#PrimaryButton:hover {{
    background-color: {t["primary_hover"]};
    border-color: {t["primary_hover"]};
}}

QPushButton#PrimaryButton:pressed {{
    background-color: {t["primary_pressed"]};
}}

QPushButton#PrimaryButton:disabled {{
    background-color: {t["primary_disabled"]};
    border-color: {t["primary_disabled"]};
    color: {t["primary_text"]};
}}

QPushButton#GhostButton {{
    background-color: transparent;
    border: 1px solid transparent;
    color: {t["ghost_text"]};
    padding: 6px 12px;
    border-radius: 8px;
}}

QPushButton#GhostButton:hover {{
    background-color: {t["ghost_hover_bg"]};
    border-color: {t["ghost_hover_border"]};
}}

QWidget#PlatformBar {{
    background: transparent;
    min-height: 28px;
    max-height: 28px;
}}

QLabel#PlatformLabel {{
    color: {t["text_secondary"]};
    font-size: 12px;
    font-weight: 500;
    background: transparent;
}}

QFrame#SegmentedTrack {{
    background-color: {t["segment_track"]};
    border: 1px solid {t["card_border"]};
    border-radius: 10px;
    min-height: 28px;
    max-height: 28px;
}}

QPushButton#SegmentButton {{
    background-color: transparent;
    color: {t["text_secondary"]};
    border: none;
    border-radius: 7px;
    padding: 4px 10px;
    font-size: 13px;
    min-height: 0;
    max-height: 20px;
    font-weight: 400;
}}

QPushButton#SegmentButton:hover {{
    background-color: {t["tab_hover"]};
    border: none;
}}

QPushButton#SegmentButton[selected="true"] {{
    background-color: {t["content_panel_bg"]};
    color: {t["text"]};
    font-weight: 600;
    border: none;
}}

QPushButton#SegmentButton[selected="true"]:hover {{
    background-color: {t["content_panel_bg"]};
    border: none;
}}

QLabel#QrPlaceholder {{
    border: 1px dashed {t["qr_placeholder_border"]};
    border-radius: 14px;
    background: {t["qr_placeholder_bg"]};
    color: {t["qr_placeholder_text"]};
    font-size: 12px;
}}

QLabel#QrImage {{
    border: 1px solid {t["qr_image_border"]};
    border-radius: 14px;
    background: {t["qr_image_bg"]};
}}

QScrollArea {{
    border: none;
    background: transparent;
}}

QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px;
}}

QScrollBar::handle:vertical {{
    background: {t["card_border"]};
    border-radius: 4px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {t["accent"]};
}}

QPlainTextEdit#LogView {{
    background-color: {t["log_bg"]};
    color: {t["log_text"]};
    border: 1px solid {t["log_border"]};
    border-radius: 10px;
    font-family: Menlo, Monaco, "PingFang SC", monospace;
    font-size: 11px;
    line-height: 1.55;
    padding: 10px 14px;
}}
"""


def apply_app_theme(app: QApplication, theme_id: str | None = None) -> str:
    selected = normalize_theme_id(theme_id or DEFAULT_THEME)
    app.setStyleSheet(build_stylesheet(selected))
    font = QFont()
    for family in (
        ".AppleSystemUIFont",
        "PingFang SC",
        "SF Pro Text",
        "Helvetica Neue",
        "Microsoft YaHei UI",
    ):
        probe = QFont(family)
        if probe.exactMatch() or family.startswith("."):
            font.setFamily(family)
            break
    font.setPointSize(13)
    app.setFont(font)
    if theme_id:
        save_theme(selected)
    return selected
