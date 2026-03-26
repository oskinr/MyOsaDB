import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os

# --- Глобальные переменные ---
db_path = None

# --- ФУНКЦИИ СО СТАРОЙ ЛОГИКОЙ (оставляем без изменений) ---
def perform_sql_query_old(db_path, result_text, include_payment_before_tenth):
    otchet = combo_type.get() 
    messagebox.showinfo('Внимание',f'Посмотрим в отчете: {otchet}')  

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    condition = "true" if include_payment_before_tenth else "false"
    query = f"""SELECT id AS айди,
                 name AS имя,
                 note2 AS примечание
                 FROM csoparams
                 WHERE name LIKE '{otchet}%'
                 AND deleted LIKE 0
                 AND parameter LIKE '%"opl_do_10","c_class":"bool","checked":{condition}%';"""
    
    try:
        cursor.execute(query)
        results = cursor.fetchall()
    except sqlite3.Error as e:
        messagebox.showerror("Ошибка", f"Ошибка выполнения запроса: {e}")
        results = []
    finally:
        conn.close()

    result_text.delete(1.0, tk.END)
    if results:
        output = "\n".join(", ".join(map(str, row)) for row in results)
        result_text.insert(tk.END, output)
    
    messagebox.showinfo("Выполнено", f"Запрос выполнен. Найдено {len(results)} записей.")


# --- ФУНКЦИИ С НОВОЙ ЛОГИКОЙ (исправленная версия) ---
def perform_sql_query_new(db_path, result_text, payment_choice):
    otchet = combo_type.get() 
    messagebox.showinfo('Внимание',f'Будем искать в отчетах: {otchet}')

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Проверяем наличие таблицы и нужных колонок
        cursor.execute("PRAGMA table_info(csoparams)")
        columns = {col[1] for col in cursor.fetchall()}
        required = {'id', 'name', 'note2', 'parameter'}
        if not required.issubset(columns):
            missing = required - columns
            messagebox.showerror("Ошибка", f"В таблице отсутствуют необходимые колонки: {', '.join(missing)}")
            return

        # --- НОВАЯ ЛОГИКА ФИЛЬТРАЦИИ ---
        # Формируем шаблон для поиска в JSON-тексте
        if payment_choice == '1':
            like_pattern = '%"value": "1", "name": "take_opl", "selected": true%'
            message_filter = "Оплата до 10 числа"
        elif payment_choice == '2':
            like_pattern = '%"value": "2", "name": "take_opl", "selected": true%'
            message_filter = "Оплата до 15 числа"
        elif payment_choice == '3': # '3' - все оплаты (ИСПРАВЛЕННАЯ ЛОГИКА)
            like_pattern = '%"value": "3", "name": "take_opl", "selected": true%'
            message_filter = "Все оплаты"
        
        # Базовая часть запроса
        query = f"""SELECT id AS айди, name AS имя, note2 AS примечание
                   FROM csoparams 
                   WHERE name like '{otchet}%'
                     AND deleted LIKE 0"""
        
        # Добавляем условие поиска по JSON-полю
        query += f""" AND parameter LIKE '{like_pattern}';"""
        cursor.execute(query)
        results = cursor.fetchall()

    except sqlite3.Error as e:
        messagebox.showerror("Ошибка базы данных", f"Не удалось выполнить запрос: {e}")
        results = []
    finally:
        conn.close()

    result_text.delete(1.0, tk.END)
    if results:
        output = "\n".join(", ".join(map(str, row)) for row in results)
        result_text.insert(tk.END, output)
    
    messagebox.showinfo("Выполнено", f"Фильтр: '{message_filter}'. Найдено {len(results)} записей.")


# --- ОСНОВНАЯ ЛОГИКА ИНТЕРФЕЙСА ---
root = tk.Tk()
root.title("Работа с базой данных SQLite")
root.geometry("700x560")


# Получаем путь к текущему скрипту и добавляем к нему имя иконки
current_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(current_dir, 'osa.ico')

# Проверяем, существует ли файл, чтобы избежать ошибок
if os.path.exists(icon_path):
    root.iconbitmap(icon_path)
else:
    print(f"Предупреждение: Иконка не найдена по пути {icon_path}")



# Фрейм для выбора режима работы (старый или новый)
mode_var = tk.StringVar(value="old")
mode_frame = tk.Frame(root)
mode_frame.pack(pady=5)

tk.Radiobutton(mode_frame, text="Старый режим", variable=mode_var, value="old").pack(side=tk.LEFT)
tk.Radiobutton(mode_frame, text="Новый режим", variable=mode_var, value="new").pack(side=tk.LEFT)

tk.Label(mode_frame, text="Выбрать отчет:").pack(side="left")
combo_type = ttk.Combobox(mode_frame, values=["01.03.07", "01.03.11"], state="readonly", width=10)
combo_type.pack(side="left", padx=5)
combo_type.current(0) # Устанавливаем "Период" по умолчанию

# Инициализируем  переменную
# otchet = combo_type.get() 
# messagebox.showinfo('Внимание',f'Элемент будет вставлен после строки: {otchet}')

# --- БЛОК СТАРЫХ РАДИОКНОПОК ---
old_radio_frame = tk.Frame(root)
old_radio_frame.pack(pady=10)
old_radio_frame.pack_forget() # Скроем по умолчанию

payment_option_old = tk.BooleanVar(value=True) 
tk.Radiobutton(old_radio_frame, text="Оплата до 10 числа", variable=payment_option_old, value=True).grid(row=0, column=0)
tk.Radiobutton(old_radio_frame, text="Нет", variable=payment_option_old, value=False).grid(row=0, column=1)

# --- БЛОК НОВЫХ РАДИОКНОПОК ---
new_radio_frame = tk.Frame(root)
new_radio_frame.pack(pady=10)
new_radio_frame.pack_forget() # Скроем по умолчанию

payment_option_new = tk.StringVar(value="3")
tk.Radiobutton(new_radio_frame, text="Учитывать оплаты до 10 числа", variable=payment_option_new, value="1").pack(anchor='w')
tk.Radiobutton(new_radio_frame, text="Учитывать оплаты до 15 числа", variable=payment_option_new, value="2").pack(anchor='w')
tk.Radiobutton(new_radio_frame, text="Учитывать все оплаты", variable=payment_option_new, value="3").pack(anchor='w')

# Функция для переключения видимости блоков радио-кнопок в зависимости от режима
def toggle_mode(*args):
    if mode_var.get() == "old":
        new_radio_frame.pack_forget()
        old_radio_frame.pack(pady=10)
    else:
        old_radio_frame.pack_forget()
        new_radio_frame.pack(pady=10)

mode_var.trace_add('write', toggle_mode) 
toggle_mode() # Инициализация интерфейса при запуске


# Кнопка для выбора файла базы данных
def select_database():
    global db_path
    path = filedialog.askopenfilename(filetypes=(("SQLite files", "*.db;*.db3"), ("All files", "*.*")))
    if path:
        db_path = path
        messagebox.showinfo("Успешно", f"База данных выбрана: {os.path.basename(db_path)}")
    else:
         messagebox.showwarning("Внимание", "Выбор базы отменён.")

select_db_btn = tk.Button(root, text="Выбрать базу данных", command=select_database)
select_db_btn.pack(pady=10)

# Кнопка для выполнения запроса (вызывает нужную функцию в зависимости от режима)
def execute_sql_query():
    if not db_path or not os.path.isfile(db_path):
         messagebox.showwarning("Внимание", "Сначала выберите существующую базу данных!")
         return

    current_mode = mode_var.get()

    if current_mode == "old":
        flag = payment_option_old.get() 
        perform_sql_query_old(db_path, result_text, flag)
    else: 
        choice = payment_option_new.get()
        perform_sql_query_new(db_path, result_text, choice)

execute_sql_btn = tk.Button(root, text="Выполнить SQL-запрос", command=execute_sql_query)
execute_sql_btn.pack(pady=10)

# Текстовое поле для вывода результатов
result_text = tk.Text(root, wrap=tk.WORD, height=20, width=80)
result_text.pack(padx=10, pady=10)

root.mainloop()