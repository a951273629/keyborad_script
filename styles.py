"""集中管理界面配色、间距和控件状态。"""

APP_STYLE = """
QWidget { font-family: "Microsoft YaHei UI", "Segoe UI"; font-size: 13px; color: #23313a; }
QMainWindow, QDialog { background: #f5f7f8; }
QFrame#topBar { background: #ffffff; border-bottom: 1px solid #dce3e6; }
QFrame#sidebar { background: #eef3f3; border-right: 1px solid #dce3e6; }
QFrame#content { background: #ffffff; }
QLabel#appTitle { font-size: 19px; font-weight: 700; color: #17292b; }
QLabel#sectionTitle { font-size: 20px; font-weight: 700; color: #17292b; }
QLabel#sidebarTitle { font-size: 15px; font-weight: 700; }
QLabel#mutedText, QLabel#hint { color: #64747b; }
QLabel#fieldLabel { font-weight: 600; }
QLabel#statusIdle { color: #63757a; font-weight: 600; }
QLabel#statusRunning { color: #087b67; font-weight: 700; }
QLabel#errorBanner { background: #fff0ee; color: #a33e35; border: 1px solid #efcbc6; border-radius: 5px; padding: 9px 12px; }
QLabel#successBanner { background: #e7f5ef; color: #087b67; border: 1px solid #bde3d0; border-radius: 5px; padding: 9px 12px; }
QLabel#healthAccent { color: #bc514e; font-weight: 700; }
QLabel#energyAccent { color: #087f83; font-weight: 700; }
QLineEdit, QDoubleSpinBox, QSpinBox { background: #ffffff; border: 1px solid #cbd6d9; border-radius: 5px; min-height: 32px; padding: 1px 9px; selection-background-color: #147d78; }
QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus { border-color: #13867e; }
QLineEdit:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled { background: #f3f5f5; color: #8b989c; }
QPushButton { background: #ffffff; border: 1px solid #cad5d7; border-radius: 5px; min-height: 34px; padding: 0 13px; font-weight: 600; }
QPushButton:hover { background: #f1f7f6; border-color: #82b8b2; }
QPushButton:disabled { color: #a4afb1; background: #f3f5f5; border-color: #e0e5e6; }
QPushButton#primaryButton { color: white; background: #087f73; border-color: #087f73; min-width: 94px; }
QPushButton#primaryButton:hover { background: #076d63; }
QPushButton#stopButton { color: #9c3734; background: #fff6f5; border-color: #e6bab6; min-width: 94px; }
QPushButton#dangerButton { color: #a33e35; border-color: #e8cfcb; }
QPushButton#iconButton { min-width: 32px; max-width: 32px; padding: 0; font-size: 18px; }
QPushButton#iconButton:hover { color: #a33e35; background: #fff2f0; border-color: #e8cfcb; }
QCheckBox { spacing: 9px; }
QCheckBox::indicator { width: 17px; height: 17px; }
QTabWidget::pane { border: 0; background: #ffffff; }
QTabBar::tab { color: #596b70; padding: 13px 19px; border-bottom: 2px solid transparent; font-weight: 600; }
QTabBar::tab:selected { color: #087f73; border-bottom-color: #087f73; }
QTabBar::tab:hover { color: #087f73; }
QScrollArea { border: 0; background: transparent; }
QScrollArea > QWidget > QWidget { background: transparent; }
QFrame#ruleHeader { background: #f2f6f6; border: 1px solid #e1e8e9; border-radius: 5px; }
QFrame#ruleRow, QFrame#featureRow { background: #ffffff; border-bottom: 1px solid #e6ecee; }
QFrame#windowRow { border: 1px solid transparent; border-radius: 5px; background: transparent; }
QFrame#windowRow[selected="true"] { background: #ffffff; border-color: #c9e1dd; }
QFrame#windowRow:hover { background: #ffffff; }
QLabel#windowName { font-weight: 600; }
QLabel#preview { background: #f1f7f5; border: 1px solid #d4e9e3; border-radius: 5px; padding: 12px; font-weight: 600; }
QListWidget { border: 1px solid #dce4e6; border-radius: 5px; background: #ffffff; padding: 5px; }
QListWidget::item { min-height: 52px; padding: 5px 8px; }
QListWidget::item:selected { background: #dcefeb; color: #174d49; }
"""
