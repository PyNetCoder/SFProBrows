import sys
import os
import json
import ctypes
from datetime import datetime
from pathlib import Path
from loguru import logger
from icecream import ic
from PySide6.QtCore import QUrl, QDir
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QToolBar, QLineEdit, QWidget, QVBoxLayout, QProgressBar, QMessageBox, QFileDialog
from PySide6.QtGui import QAction
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage, QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo

# AppData/Local/SFProBrows/logs klasör yapısı oluşturuluyor
BASE_DIR = Path(__file__).resolve().parent
LOCAL_APPDATA = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
LOG_DIR = LOCAL_APPDATA / "SFProBrows" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logger.remove()
logger.add(sys.stderr, level="DEBUG", format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {function}:{line} - {message}")
logger.add(LOG_DIR / "browser_{time:YYYY-MM-DD}.log", rotation="00:00", level="INFO", encoding="utf-8")

ic.configureOutput(prefix="DEBUG-IC | ", outputFunction=logger.debug)

if hasattr(os, "add_dll_directory"):
    try:
        os.add_dll_directory(str(BASE_DIR))
    except Exception as e:
        logger.warning(f"DLL error: {e}")

try:
    c_dll_path = BASE_DIR / "sfpb_core.dll"
    if not c_dll_path.exists():
        raise FileNotFoundError(f"C DLL missing: {c_dll_path}")
    c_motor = ctypes.CDLL(str(c_dll_path))
    c_motor.kontrol_et_guvenlik.argtypes = [ctypes.c_char_p]
    c_motor.kontrol_et_guvenlik.restype = ctypes.c_int
    logger.success("C Core DLL successfully connected!")
except Exception as e:
    logger.exception(f"C DLL load failure: {e}")
    c_motor = None

try:
    cpp_dll_path = BASE_DIR / "sfpb_engine.dll"
    if not cpp_dll_path.exists():
        raise FileNotFoundError(f"C++ DLL missing: {cpp_dll_path}")
    cpp_motor = ctypes.CDLL(str(cpp_dll_path), winmode=0)
    cpp_motor.kelime_kontrol.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
    cpp_motor.kelime_kontrol.restype = ctypes.c_int
    logger.success("C++ Core DLL successfully connected!")
except Exception as e:
    logger.exception(f"C++ DLL load failure: {e}")
    cpp_motor = None

net_motor_active = False
logger.warning("C# Engine bypassed.")

class AdvancedDataSaverInterceptor(QWebEngineUrlRequestInterceptor):
    def __init__(self):
        super().__init__()
        # Reklam ve veri tüketen harici havuzlar
        self.block_keywords = [
            "ads.", "analytics", "doubleclick", "telemetry", "google-analytics",
            "statcounter", "pixel.wp", "facebook.com", "adservice", "advertisement",
            "adserver", "adsystem", "popunder", "banner", "tracking"
        ]
        
        # Güvenli kabul edilen ve ikon/logo barındıran kritik CDN ve statik kaynaklar
        self.safe_keywords = [
            "gstatic.com", "fonts.", "favicon", "logo", "icon", "theme"
        ]

    def interceptRequest(self, info: QWebEngineUrlRequestInfo):
        try:
            url_str = info.requestUrl().toString().lower()
            res_type_str = str(info.resourceType()).lower()
            
            # Ana sitenin domaini ile isteğin yapıldığı domaini karşılaştırıyoruz
            first_party_url = info.firstPartyUrl().toString().lower()
            
            # 1. Reklam/Domain Filtresi (Her zaman en yüksek öncelik)
            if any(keyword in url_str for keyword in self.block_keywords):
                logger.info(f"SFPB AdBlocker: Blocked Ad/Tracker -> {url_str[:60]}...")
                info.block(True)
                return

            # 2. Akıllı Medya Filtreleme
            if "image" in res_type_str or "media" in res_type_str:
                # Eğer görsel kritik bir altyapıdan geliyorsa veya sitenin kendi yerel logosuysa izin ver
                if any(safe in url_str for safe in self.safe_keywords):
                    return
                
                # Görsel harici (3. parti) bir ajanstan veya reklam ağından geliyorsa engelle
                # Sitenin kendi içindeki resimlere izin vererek tasarımı koruyoruz
                from urllib.parse import urlparse
                site_domain = urlparse(first_party_url).netloc
                req_domain = urlparse(url_str).netloc
                
                if site_domain and req_domain and site_domain != req_domain:
                    logger.info(f"SFPB AdBlocker: Blocked 3rd Party Image -> {url_str[:60]}...")
                    info.block(True)
                    return
                
        except Exception:
            pass


class SFProBrows(QMainWindow):
    def __init__(self, profile):
        super().__init__()
        logger.info("SFProBrows starting...")
        self.custom_profile = profile
        self.HISTORY_FILE = BASE_DIR / "history.json"
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
        self.load_extensions()
        self.add_new_tab(QUrl("https://google.com"), "Home")
        self.showMaximized()
    def active_browser(self) -> QWebEngineView:
        return self.tabs.currentWidget()
    @logger.catch
    def add_new_tab(self, qurl=None, title="New Tab"):
        if qurl is None:
            qurl = QUrl("https://google.com")
        logger.info(f"Tab open: {qurl.toString()}")
        browser = QWebEngineView()
        page = QWebEnginePage(self.custom_profile, browser) 
        browser.setPage(page)
        browser.setUrl(qurl)
        ic(browser)
        index = self.tabs.addTab(browser, title)
        self.tabs.setCurrentIndex(index)
        browser.urlChanged.connect(lambda q: self.update_url_bar(q, browser))
        browser.loadStarted.connect(lambda: self.set_loading_state(True))
        browser.loadProgress.connect(self.update_loading_progress)
        browser.loadFinished.connect(lambda success, b=browser: self.handle_load_finished(success, b))
    def handle_load_finished(self, success, browser):
        self.set_loading_state(False)
        index = self.tabs.indexOf(browser)
        if index == -1:
            return
        if success:
            title = browser.page().title()
            if title:
                self.tabs.setTabText(index, title[:15] + "...")
            url_str = browser.url().toString()
            if url_str and url_str != "about:blank":
                self.save_to_json(url_str, title)
        else:
            logger.error(f"Page load fail: {browser.url().toString()}")
    def save_to_json(self, url, title):
        try:
            history_list = []
            if self.HISTORY_FILE.exists() and self.HISTORY_FILE.stat().st_size > 0:
                with open(self.HISTORY_FILE, "r", encoding="utf-8") as f:
                    try:
                        history_list = json.load(f)
                    except json.JSONDecodeError:
                        logger.warning("History file corrupted, resetting.")
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
        except Exception as e:
            logger.exception(f"History save error: {e}")
    def go_home(self):
        if self.active_browser():
            self.active_browser().setUrl(QUrl("https://google.com"))
    def navigate_to_url(self):
        text = self.url_bar.text().strip()
        if not text:
            return
        if "." not in text or " " in text:
            qurl = QUrl(f"https://google.com{text}")
        else:
            qurl = QUrl(text)
            if qurl.scheme() == "":
                qurl.setScheme("https")
        if self.active_browser():
            logger.info(f"Navigate: {qurl.toString()}")
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
            logger.info(f"Tab closed, index: {index}")
            widget.deleteLater()
    def set_loading_state(self, loading):
        self.progress_bar.setVisible(loading)
    def update_loading_progress(self, progress):
        self.progress_bar.setValue(progress)
    def load_extensions(self):
        ext_dir = BASE_DIR / "extensions"
        if not ext_dir.exists():
            ext_dir.mkdir()
            logger.info("Extensions directory created.")
            return
        for ext_path in ext_dir.iterdir():
            if ext_path.is_dir() and (ext_path / "manifest.json").exists():
                try:
                    self.custom_profile.installExtension(str(ext_path))
                    logger.success(f"Extension injected: {ext_path.name}")
                except Exception as e:
                    logger.exception(f"Extension failure ({ext_path.name}): {e}")
    @staticmethod
    def handle_download_request(download):
        suggested_path = download.downloadDirectory() + QDir.separator() + download.downloadFileName()
        logger.info(f"Download detected: {download.url().toString()}")
        file_path, _ = QFileDialog.getSaveFileName(None, "Save File", suggested_path)
        if file_path:
            save_path = Path(file_path)
            download.setDownloadDirectory(str(save_path.parent))
            download.setDownloadFileName(save_path.name)
            download.stateChanged.connect(
                lambda state: logger.info(f"Downloading: {download.downloadFileName()} (State: {state})")
                if state == 2 else logger.success(f"Download complete: {download.downloadFileName()}")
            )
            download.accept()
            logger.info(f"Download started: {save_path.name}")
        else:
            download.cancel()
            logger.warning("Download cancelled by user.")
if __name__ == "__main__":
    try:
        os.environ["QTWEBENGINE_DISABLE_GPU"] = "1"
        sys.argv.append("--disable-gpu")
        sys.argv.append("--software-rendering-backend")
        
        # 1. Qt Çekirdeği Başlatılıyor
        app = QApplication(sys.argv)
        
        # 2. Profil Alınıyor ve Veri Tasarrufu Aktif Ediliyor (Yeni Entegrasyon)
        profile = QWebEngineProfile.defaultProfile()
        data_saver_interceptor = AdvancedDataSaverInterceptor()
        profile.setUrlRequestInterceptor(data_saver_interceptor)
        
        # 3. Depolama ve Önbellek Klasör Ayarları
        local_appdata = Path(os.environ.get("LOCALAPPDATA", str(BASE_DIR)))
        secure_storage = local_appdata / "SFProBrows" / "Storage"
        secure_cache = local_appdata / "SFProBrows" / "Cache"
        secure_storage.mkdir(parents=True, exist_ok=True)
        secure_cache.mkdir(parents=True, exist_ok=True)
        
        profile.setPersistentStoragePath(str(secure_storage))
        profile.setCachePath(str(secure_cache))
        
        # 4. İndirme Yöneticisi Bağlantısı ve Pencere Başlangıcı
        profile.downloadRequested.connect(SFProBrows.handle_download_request)
        browser_window = SFProBrows(profile)
        browser_window.show()
        
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"App crashed: {e}")
