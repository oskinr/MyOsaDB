import tkinter as tk
from PIL import Image, ImageTk
import os
import json
import urllib.request
import urllib.error
from tkinter import messagebox
import subprocess
import queue
import threading
import win32api
import sys

# --- Настройка URL-открывателя ---
opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
urllib.request.install_opener(opener)


def resource_path(relative_path):
    """Получить абсолютный путь к ресурсу, работает для dev и для PyInstaller."""
    try:
        # PyInstaller создает временную папку и сохраняет путь в _MEIPASS
        base_path = sys._MEIPASS
        print(f"Запуск из собранного файла. Путь к ресурсам: {base_path}") # Для отладки
    except AttributeError:
        # Если исключения нет, то мы запускаем код напрямую (во время разработки)
        base_path = os.path.abspath(".")
 
    return os.path.join(base_path, relative_path)


# Класс для отображения анимации GIF
class AnimatedGif(tk.Label):
    def __init__(self, master, path):
        super().__init__(master)
        self.frames = []
        self.delay = 100
        self.current_frame = 0
        self.load_gif(path)
        self.start_animation()
    
    def load_gif(self, path):
        img = Image.open(path)
        while True:
            frame = ImageTk.PhotoImage(img.copy())
            self.frames.append(frame)
            try:
                img.seek(len(self.frames))
            except EOFError:
                break
    
    def start_animation(self):
        if self.frames:
            self.configure(image=self.frames[self.current_frame])
            self.current_frame = (self.current_frame + 1) % len(self.frames)
            self.after(self.delay, self.start_animation)


# Сравнение версий
def compare_versions(current_version, latest_version):
    if not current_version or not latest_version:
        return False
    return list(map(int, current_version.split("."))) < list(map(int, latest_version.split(".")))


# Загрузка файла в отдельном потоке
def download_file(url, output_filename, window):
    """Скачивает файл по ссылке в фоновом потоке."""
    def _download():
        try:
            with urllib.request.urlopen(url) as response:
                data = response.read()
            with open(output_filename, "wb") as out_file:
                out_file.write(data)
            window.update_status(f"✅ Файл {output_filename} успешно скачан.")
        except Exception as e:
            window.update_status(f"❌ Ошибка при скачивании {output_filename}: {e}")
    
    thread = threading.Thread(target=_download, daemon=True)
    thread.start()


def fetch_all_release_assets(owner, repo, window):
    """
    Запрашивает последний релиз репозитория.
    Возвращает список файлов или None при ошибке.
    """
    try:
        api_url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(api_url, headers=headers)
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode("utf-8"))
            release_version = data.get("tag_name", "").lstrip("v")
            assets = data.get("assets", [])
            
            assets_info = []
            for asset in assets:
                assets_info.append({
                    "name": asset["name"],
                    "download_url": asset["browser_download_url"],
                    "version": release_version
                })
            return assets_info

    except urllib.error.HTTPError as e:
        window.update_status(f"[ОШИБКА] Сервер вернул код: {e.code}")
        return None
    except Exception as err:
        window.update_status(f"[ОШИБКА] {err}")
        return None


def extract_product_version_from_exe(file_path, window):
    """
    Извлекает версию продукта из EXE-файла.
    Возвращает версию как строку или None в случае ошибки.
    """
    try:
        info = win32api.GetFileVersionInfo(file_path, '\\')
        ms = info['FileVersionMS']
        ls = info['FileVersionLS']
        return f"{win32api.HIWORD(ms)}.{win32api.LOWORD(ms)}.{win32api.HIWORD(ls)}.{win32api.LOWORD(ls)}"
    except Exception:
        return None


REQUIRED_FILES = ["osa_db.exe", "osa_upd.exe", "osa_sql.exe"]
SETUP_FILE_NAME = "MyOsdbSetup.exe"
MAIN_EXECUTABLE = "osa_db.exe"
LAUNCHER_DIR = os.getcwd()


def launch_and_close(window):
    """Запускает основной файл и закрывает лаунчер."""
    exe_path = os.path.join(LAUNCHER_DIR, MAIN_EXECUTABLE)
    
    if os.path.exists(exe_path):
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            subprocess.Popen([exe_path], creationflags=creationflags)
            window.update_status(f"🚀 Запуск {MAIN_EXECUTABLE}...")
        except Exception as e:
            window.update_status(f"[ОШИБКА ЗАПУСКА] {e}")
    
    window.fade_out()


# --- НОВАЯ ФУНКЦИЯ: Скачивание установщика ---
def download_setup_file(assets_info, window):
    """
    Главная функция для работы с установщиком.
    Проверяет наличие файла -> Если нет, ищет на сервере -> Скачивает -> Запускает.
    """
    # 1. ПУТЬ К ФАЙЛУ И ПРОВЕРКА ЕГО НАЛИЧИЯ В ПАПКЕ
    setup_path = os.path.join(LAUNCHER_DIR, SETUP_FILE_NAME)
    
    if os.path.exists(setup_path):
        # Файл уже есть! Пропускаем скачивание и сразу запускаем.
        window.update_status(f"⚡ Установщик уже найден. Запускаем {SETUP_FILE_NAME}...")
        
        def run_existing_setup():
            try:
                subprocess.Popen([SETUP_FILE_NAME])
                window.fade_out()
            except Exception as e:
                window.update_status(f"❌ Ошибка при запуске: {e}")
        
        window.master.after(1000, run_existing_setup)
        return # Выходим из функции

    # 2. ЕСЛИ ФАЙЛА НЕТ, ИЩЕМ ЕГО В СПИСКЕ АКТИВОВ (НА СЕРВЕРЕ)
    # Используем lower() для игнорирования регистра букв (MyFile.exe vs myfile.exe)
    target_name_lower = SETUP_FILE_NAME.lower()
    setup_asset = None
    for asset in assets_info:
        if asset["name"].lower() == target_name_lower:
            setup_asset = asset
            break # Нашли, выходим из цикла

    # 3. ЕСЛИ ФАЙЛ НАЙДЕН НА СЕРВЕРЕ, КАЧАЕМ И ЗАПУСКАЕМ
    if setup_asset:
        window.update_status(f"📦 Установщик не найден. Начинаю загрузку '{setup_asset['name']}'...")
        
        def on_download_complete():
            """Вызывается только после полного завершения скачивания."""
            try:
                window.update_status("🚀 Загрузка завершена. Запуск установщика...")
                subprocess.Popen([SETUP_FILE_NAME])
                window.fade_out()
            except Exception as e:
                window.update_status(f"❌ Ошибка при запуске: {e}")

        # Запускаем скачивание в отдельном потоке
        download_file(setup_asset["download_url"], SETUP_FILE_NAME, window)
        
        # --- ТАЙМЕР ДЛЯ ПРОВЕРКИ ЗАВЕРШЕНИЯ СКАЧИВАНИЯ ---
        def check_download_done():
            """Проверяет, живы ли еще потоки скачивания."""
            # Находим все потоки, кроме главного
            active_downloads = [t for t in threading.enumerate() if t.name != 'MainThread']
            
            if not active_downloads:
                # Если потоков нет, значит скачивание завершено
                on_download_complete()
            else:
                # Если еще качается, проверяем снова через 0.5 сек
                window.master.after(500, check_download_done)
        
        # Запускаем первую проверку
        check_download_done()

    # 4. ЕСЛИ ФАЙЛА НЕТ НИГДЕ
    else:
        window.update_status(f"⛔ Критическая ошибка: Установщик {SETUP_FILE_NAME} не найден на сервере!")
        window.master.after(5000, window.fade_out) # Даем 5 секунд на прочтение ошибки

def offer_update_if_available(owner_main, repo_main, window):
    """
    Главная логика: проверяет наличие и обновления всех файлов.
    Запускает приложение ТОЛЬКО ПОСЛЕ завершения всех загрузок.
    """
    def put_status(text):
        window.message_queue.put(text)

    def check_and_launch():
        """Проверяет, закончились ли загрузки, и запускает игру."""
        active_downloads = [t for t in threading.enumerate() if t.name != 'MainThread']
    
        if not active_downloads:
            launch_and_close(window)
        else:
            window.master.after(1000, check_and_launch)
    
    put_status("🔍 Проверка файлов...")
    
    # --- 1. Проверка недостающих файлов ---
    missing_files = [f for f in REQUIRED_FILES if not os.path.exists(os.path.join(LAUNCHER_DIR, f))]
    
    if missing_files:
        # Проверяем, отсутствуют ВООБЩЕ ВСЕ файлы?
        all_files_missing = len(missing_files) == len(REQUIRED_FILES)
        
        put_status(f"⬇️ Обнаружены недостающие файлы: {', '.join(missing_files)}.")
        
        remote_assets = fetch_all_release_assets(owner_main, repo_main, window)
        
        if remote_assets is None:
            put_status("⛔ Не удалось получить список файлов с сервера.")
            return

        if all_files_missing:
            # --- ИСПРАВЛЕННАЯ ЛОГИКА ---
            # Если нет ни одного файла — предлагаем скачать установщик
            # Мы не закрываем окно сразу, а передаем ему список активов
            # и оно само закроется после скачивания.
            download_setup_file(remote_assets, window)
            
            # ВАЖНО: Убери эту строку!
            # window.master.after(1000, window.fade_out) 
            # return 
        else:
            # Если не хватает только части файлов — качаем их по отдельности
            put_status("⬇️ Загрузка недостающих компонентов...")
            for file_to_download in missing_files:
                asset = next((a for a in remote_assets if a["name"] == file_to_download), None)
                if asset:
                    download_file(asset["download_url"], file_to_download, window)
                else:
                    put_status(f"⚠️ Файл {file_to_download} не найден на сервере!")
        
        check_and_launch()
        return

    # --- 2. Проверка обновлений для существующих файлов ---
    else:
        put_status("✅ Все файлы найдены. Проверка обновлений...")
        
        remote_assets = fetch_all_release_assets(owner_main, repo_main, window)
        
        if remote_assets is None:
            put_status("⛔ Не удалось проверить наличие обновлений.")
            check_and_launch() # Пробуем запустить игру даже без проверки обновлений
            return

        for local_filename in REQUIRED_FILES:
            local_path = os.path.join(LAUNCHER_DIR, local_filename)
            
            matching_remote_asset = next((asset for asset in remote_assets if asset["name"] == local_filename), None)
            
            if not matching_remote_asset:
                continue

            current_version = extract_product_version_from_exe(local_path, window) or "0.0.0"
            remote_version = matching_remote_asset["version"]
            
            if compare_versions(current_version, remote_version):
                message = (f"🆕 Доступно обновление для {local_filename}!\n"
                        f"📦 Текущая: {current_version} | Новая: {remote_version}")
                put_status(message)
                
                result = messagebox.askyesno(
                    "Обновление найдено",
                    message + "\n\nУстановить сейчас?"
                )
                
                if result:
                    put_status(f"⬇️ Загрузка обновления для {local_filename}...")
                    download_file(matching_remote_asset["download_url"], local_filename, window)
        
        put_status("✅ Проверка завершена.")
        check_and_launch()


class UpdateWindow:
    def __init__(self, master):
        self.master = master
        self.master.title("Launcher")
        self.master.geometry("310x210")
        
        # Центрирование окна на экране (ИСПРАВЛЕНО: 210 вместо 680)
        ws = self.master.winfo_screenwidth()
        hs = self.master.winfo_screenheight()
        x = (ws // 2) - (310 // 2)
        y = (hs // 2) - (210 // 2) 
        y = y - 220 
        self.master.geometry('+{}+{}'.format(x, y))
        



        
        icon_path = resource_path('osa.ico')
        try:
            self.master.iconbitmap(icon_path)
        except Exception as e:
            print(f"Предупреждение: Не удалось загрузить иконку: {e}")
        
        self.text_label = tk.Label(master, text="", font=("Helvetica", 18))
        self.text_label.pack(pady=10)
        
        gif_path = resource_path('osa.gif')
        
        
        self.gif_panel = AnimatedGif(master, gif_path)
        self.gif_panel.pack(expand=True, fill="both")
    
        self.status_label = tk.Label(master, text="", justify="left", wraplength=280)
        self.status_label.pack(pady=10)
        
        # --- ИСПРАВЛЕННЫЙ МЕТОД ВНУТРИ КЛАССА ---
        self.animate_text("Osa")
    
        self.message_queue = queue.Queue()
        self.check_queue()
    
    
    def check_queue(self):
        while not self.message_queue.empty():
            try:
                message = self.message_queue.get_nowait()
                self.update_status(message)
            except queue.Empty:
                pass
        
        self.master.after(100, self.check_queue)
    
    # Метод animate_text теперь находится здесь!
    def animate_text(self, text):
        index = 0
        def type_letter():
            nonlocal index
            if index < len(text):
                self.text_label.config(text=self.text_label.cget("text") + text[index])
                index += 1
                self.master.after(800, type_letter)  
            else:
                pass 
        type_letter()
    
    def update_status(self, text):
        self.status_label.config(text=text)
        self.master.update_idletasks()

    def fade_out(self):
        alpha = float(self.master.attributes("-alpha"))
        if alpha > 0:
            alpha -= 0.05
            self.master.attributes("-alpha", alpha)
            self.master.after(50, self.fade_out)
        else:
            self.master.destroy()


if __name__ == "__main__":
    owner = "oskinr"
    repo = "MyOsaDB"
    
    root = tk.Tk()
    window = UpdateWindow(root)
    
    offer_update_if_available(owner, repo, window)
    
    root.mainloop()