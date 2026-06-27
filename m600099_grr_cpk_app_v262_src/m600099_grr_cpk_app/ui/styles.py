# ──────────────────────────────────────────────
#  UI Stylesheet
# ──────────────────────────────────────────────

MAIN_STYLE = """
/* ── Reset ── */
QWidget { font-family: "Segoe UI", Arial, sans-serif; font-size: 9pt; }
QMainWindow { background: #f5f6fa; }

/* ── Header ── */
.header-widget {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #1a2a6c, stop:1 #1e3c72);
    padding: 5px 14px;
}
.header-title { color: white; font-size: 11pt; font-weight: bold; }
.header-sub   { color: #aab4d4; font-size: 8pt; }

/* ── Group boxes ── */
QGroupBox {
    font-weight: bold;
    border: 1px solid #d0d5dd;
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 8px;
    background: white;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 4px;
    color: #1a2a6c;
}

/* ── Buttons ── */
QPushButton {
    background: #1a2a6c;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: bold;
    min-width: 90px;
}
QPushButton:hover  { background: #253a8e; }
QPushButton:pressed{ background: #0f1a45; }
QPushButton:disabled{ background: #b0b8cc; color: #e0e4ee; }

.btn-primary { background: #1a2a6c; }
.btn-success { background: #2e7d32; }
.btn-success:hover { background: #1b5e20; }
.btn-warning { background: #e65100; }
.btn-warning:hover{ background: #bf360c; }
.btn-danger  { background: #c62828; }
.btn-danger:hover { background: #b71c1c; }

/* ── File drop zone ── */
.drop-zone {
    border: 2px dashed #90a4ae;
    border-radius: 8px;
    background: #fafafa;
    padding: 20px;
}
.drop-zone.active {
    border-color: #1a2a6c;
    background: #e8eaf6;
}

/* ── List widget (item selector) ── */
QListWidget {
    border: 1px solid #d0d5dd;
    border-radius: 4px;
    background: white;
    padding: 2px;
}
QListWidget::item {
    padding: 4px 6px;
    border-radius: 3px;
    margin: 1px 0;
}
QListWidget::item:selected {
    background: #c5cae9;
    color: #1a2a6c;
}
QListWidget::item:hover { background: #e8eaf6; }

/* ── Progress bar ── */
QProgressBar {
    border: 1px solid #d0d5dd;
    border-radius: 4px;
    text-align: center;
    background: #f0f0f0;
    height: 20px;
}
QProgressBar::chunk { background: #1a2a6c; border-radius: 3px; }

/* ── Log widget ── */
#logWidget {
    font-family: "Consolas", "Courier New", monospace;
    font-size: 8pt;
    background: #1e1e1e;
    color: #d4d4d4;
    border: 1px solid #3e3e42;
    border-radius: 4px;
    padding: 4px;
}

/* ── Status bar ── */
QStatusBar { background: #e8eaf6; color: #3949ab; font-size: 8pt; }

/* ── Tree widget ── */
QTreeWidget {
    border: 1px solid #d0d5dd;
    border-radius: 4px;
    background: white;
}
QTreeWidget::item:hover { background: #e8eaf6; }
"""
