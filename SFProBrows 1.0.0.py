import sys
import os
import json
import ctypes
import traceback
from datetime import datetime
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QToolBar, QLineEdit, QWidget, QVBoxLayout, QProgressBar, QMessageBox
from PySide6.QtGui import QAction
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage

base_dir = os.path.dirname(os.path.abspath(__file__))

if hasattr(os, "add_dll_directory"):
    try:
        os.add_dll_directory(base_dir)
    except Exception:
        pass

try:
    c_dll_path = os.path.join(base_dir, "sfpb_core.dll")
    c_motor = ctypes.CDLL(c_dll_path)
    c_motor.kontrol_et_guvenlik.argtypes = [ctypes.c_char_p]
    c_motor.kontrol_et_guvenlik.restype = ctypes.c_int
    print("[SFPB Engine]: C Core DLL successfully connected!")
except Exception as e:
    print(f"[SFPB Engine Error]: Failed to load C DLL: {e}")
    c_motor = None

try:
    cpp_dll_path = os.path.join(base_dir, "sfpb_engine.dll")
    cpp_motor = ctypes.CDLL(cpp_dll_path, winmode=0)
    cpp_motor.kelime_kontrol.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    cpp_motor.kelime_kontrol.restype = ctypes.c_int
    print("[SFPB Engine]: C++ Core DLL successfully connected!")
except Exception as e:
    print(f"[SFPB Engine Error]: Failed to load C++ DLL: {e}")
    cpp_motor = None

net_motor_active = False
print("[SFPB Engine]: C# Engine bypassed for system stability.")

class SFProBrows(QMainWindow):
    def __init__(self, profile):
        super().__init__()
        self.custom_profile = profile
        self.HISTORY_FILE = os.path.join(base_dir, "history.json")
        self.setStyleSheet("QMainWindow { background-color: #1e1e24; } QToolBar { background-color: #2a2a35; border: none; padding: 6px; spacing: 5px; } QLineEdit { background-color: #121214; color: #e0e0e0; border: 1px solid #444454; border-radius: 6px; padding: 6px 12px; font-size: 13px; font-family: 'Segoe UI'; } QLineEdit:focus { border: 1px solid #5294e2; background-color: #16161a; } QTabBar::tab { background: #2a2a35; color: #a0a0a5; padding: 8px 16px; border-top-left-radius: 6px; border-top-right-radius: 6px; font-family: 'Segoe UI'; font-size: 12px; margin-right: 2px; } QTabBar::tab:selected { background: #1e1e24; color: #ffffff; border-bottom: 2px solid #5294e2; } QTabBar::tab:hover { background: #323242; color: #ffffff; } QProgressBar { border: none; background-color: #2a2a35; height: 3px; text-align: center; } QProgressBar::chunk { background-color: #5294e2; width: 20px; }")
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.tabBarDoubleClicked.connect(self.tab_double_clicked)
        self.tabs.currentChanged.connect(self.tab_changed)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)
        main_layout.addWidget(self.tabs)
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        navigation_bar = QToolBar("Navigation")
        navigation_bar.setMovable(False)
        self.addToolBar(navigation_bar)
        def create_action(text, trigger_function):
            action = QAction(text, self)
            action.triggered.connect(trigger_function)
            return action
        navigation_bar.addAction(create_action("<-", lambda: self.active_browser().back() if self.active_browser() else None))
        navigation_bar.addAction(create_action("->", lambda: self.active_browser().forward() if self.active_browser() else None))
        navigation_bar.addAction(create_action("Refresh", lambda: self.active_browser().reload() if self.active_browser() else None))
        navigation_bar.addAction(create_action("Home", self.go_home))
        self.url_bar = QLineEdit()
        self.url_bar.setPlaceholderText("Type a URL or search Google...")
        self.url_bar.returnPressed.connect(self.navigate_to_url)
        navigation_bar.addWidget(self.url_bar)
        navigation_bar.addAction(create_action("+ New Tab", lambda: self.add_new_tab()))
        self.add_new_tab(QUrl("https://google.com"), "Home")
        self.showMaximized()

    def active_browser(self):
        return self.tabs.currentWidget()

    def add_new_tab(self, qurl=None, title="New Tab"):
        if qurl is None:
            qurl = QUrl("https://google.com")
        browser = QWebEngineView()
        page = QWebEnginePage(self.custom_profile, browser) 
        browser.setPage(page)
        browser.setUrl(qurl)
        index = self.tabs.addTab(browser, title)
        self.tabs.setCurrentIndex(index)
        browser.urlChanged.connect(lambda qurl: self.update_url_bar(qurl, browser))
        browser.loadStarted.connect(lambda: self.set_loading_state(True))
        browser.loadProgress.connect(self.update_loading_progress)
        browser.loadFinished.connect(lambda success, b=browser: self.handle_load_finished(success, b))

    def handle_load_finished(self, success, browser):
        self.set_loading_state(False)
        index = self.tabs.indexOf(browser)
        if index == -1:
            return
        title = browser.page().title()
        if title:
            self.tabs.setTabText(index, title[:15] + "...")
        url_str = browser.url().toString()
        if url_str and url_str != "about:blank":
            self.save_to_json(url_str, title)

    def save_to_json(self, url, title):
        if not os.path.exists(self.HISTORY_FILE) or os.path.getsize(self.HISTORY_FILE) == 0:
            history_list = []
        else:
            with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                try:
                    history_list = json.load(f)
                except json.JSONDecodeError:
                    history_list = []
        if history_list and history_list[-1]["url"] == url:
            return
        history_entry = {
            "title": title if title else "Unknown Title",
            "url": url,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        history_list.append(history_entry)
        with open(self.HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_list, f, ensure_ascii=False, indent=4)

    def go_home(self):
        if self.active_browser():
            self.active_browser().setUrl(QUrl("https://google.com"))

    def navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text:
            return
        if "." not in text or " " in text:
            qurl = QUrl(f"https://www.google.com/search?q={text}")
        else:
            qurl = QUrl(text)
            if qurl.scheme() == "":
                qurl.setScheme("https")
        if self.active_browser():
            self.active_browser().setUrl(qurl)

    def update_url_bar(self, qurl, browser=None):
        if browser == self.active_browser():
            self.url_bar.setText(qurl.toString())
            self.url_bar.setCursorPosition(0)

    def tab_double_clicked(self, index):
        if index == -1:
            self.add_new_tab()

    def tab_changed(self, index):
        if index != -1:
            browser = self.tabs.widget(index)
            if browser:
                self.update_url_bar(browser.url(), browser)

    def close_tab(self, index):
        if self.tabs.count() < 2:
            return
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        if widget:
            widget.deleteLater()

    def set_loading_state(self, loading):
        self.progress_bar.setVisible(loading)

    def update_loading_progress(self, progress):
        self.progress_bar.setValue(progress)

if __name__ == "__main__":
    try:
        os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"
        sys.argv.append("--disable-gpu")
        sys.argv.append("--software-rendering-backend")
        app = QApplication(sys.argv)
        profile = QWebEngineProfile.defaultProfile()
        local_appdata = os.environ.get("LOCALAPPDATA", base_dir)
        secure_storage = os.path.join(local_appdata, "SFProBrows", "Storage")
        secure_cache = os.path.join(local_appdata, "SFProBrows", "Cache")
        os.makedirs(secure_storage, exist_ok=True)
        os.makedirs(secure_cache, exist_ok=True)
        profile.setPersistentStoragePath(secure_storage)
        profile.setCachePath(secure_cache)
        browser_window = SFProBrows(profile)
        browser_window.show()
        sys.exit(app.exec())
    except Exception as e:
        with open(os.path.join(base_dir, "sfpb_crash_error.txt"), "w", encoding="utf-8") as crash_file:
            crash_file.write(traceback.format_exc())