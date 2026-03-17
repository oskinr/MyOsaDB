import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox

# Функция для выполнения SQL-запроса
def perform_sql_query(db_path, result_text, include_payment_before_tenth):
    if not db_path:
        messagebox.showwarning("Внимание", "Сначала выберите базу данных!")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Динамическое формирование SQL-запроса в зависимости от выбора пользователя
    condition = "true" if include_payment_before_tenth else "false"
    query = f"""SELECT id AS айди,
                 name AS имя,
                 note2 AS примечание
                 FROM csoparams
                 WHERE name LIKE '%01.03.07%'
                 AND parameter LIKE '%\"opl_do_10\",\"c_class\":\"bool\",\"checked\":{condition}%';"""

    cursor.execute(query)
    results = cursor.fetchall()
    conn.close()

    # Выводим результаты в текстовое поле
    output = "\n".join(", ".join(map(str, row)) for row in results)
    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, output)

    # Сообщаем пользователю о результатах
    messagebox.showinfo("Выполнено", f"Запрос выполнен. Найдено {len(results)} записей.")

# Основная логика (пример интерфейса)
root = tk.Tk()
root.title("Работа с базой данных SQLite")

# Радиокнопки для выбора варианта оплаты
payment_option = tk.StringVar(value="yes")  # Начальное значение по умолчанию
payment_radio_frame = tk.Frame(root)
payment_radio_frame.pack(pady=10)

tk.Radiobutton(payment_radio_frame, text="Да, оплата до 10 числа", variable=payment_option, value="yes").grid(row=0, column=0)
tk.Radiobutton(payment_radio_frame, text="Нет, оплата позже", variable=payment_option, value="no").grid(row=0, column=1)

# Кнопка для выбора базы данных
def select_database():
    global db_path
    db_path = filedialog.askopenfilename(filetypes=(("SQLite files", "*.db3"), ("All files", "*.*")))
    if db_path:
        messagebox.showinfo("Успешно", f"База данных {db_path} выбрана.")
    else:
        messagebox.showwarning("Внимание", "Необходимо выбрать базу данных.")

select_db_btn = tk.Button(root, text="Выбрать базу данных", command=select_database)
select_db_btn.pack(pady=10)

# Кнопка для выполнения SQL-запроса
def execute_sql_query():
    if payment_option is None:
        messagebox.showwarning("Внимание", "Выберите вариант оплаты до 10-го числа!")
        return

    if not db_path or not result_text:
        messagebox.showwarning("Внимание", "Сначала выберите базу данных и убедитесь, что интерфейс готов!")
        return

    # Передаем флаг выбора пользователя в функцию
    flag = payment_option.get() == "yes"
    perform_sql_query(db_path, result_text, flag)

execute_sql_btn = tk.Button(root, text="Выполнить SQL-запрос", command=execute_sql_query)
execute_sql_btn.pack(pady=10)

# Текстовое поле для вывода результатов
result_text = tk.Text(root, wrap=tk.WORD, height=20, width=60)
result_text.pack(padx=10, pady=10)

root.mainloop()
