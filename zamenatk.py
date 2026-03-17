import sqlite3
import json
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import pathlib
import os

# Функция для извлечения данных из базы
def fetch_data(cursor, selected_ids):
    query = f'SELECT id, parameter FROM csoparams WHERE id IN ({", ".join(map(str, selected_ids))})'
    cursor.execute(query)
    rows = cursor.fetchall()
    return {row[0]: json.loads(row[1]) for row in rows}

# Функция для поиска недостающих элементов
def find_missing_items(list1, list2):
    return [item for item in list1 if item not in list2]

# Функция для сравнения отчетов
def compare_reports(selected_ids, db_path):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Получаем данные из базы
    data_by_id = fetch_data(cursor, selected_ids)
    connection.close()

    # Получаем данные для каждого ID
    data_a = data_by_id.get(selected_ids[0], [])
    data_b = data_by_id.get(selected_ids[1], [])

    # Находим элементы, которых нет в A, но есть в B
    missing_in_a = find_missing_items(data_b, data_a)

    # Находим элементы, которых нет в B, но есть в A
    missing_in_b = find_missing_items(data_a, data_b)

    # Формируем результат
    result = ""
    if missing_in_a:
        result += f"Элементы, которых нет в отчёте {selected_ids[0]}:\n"
        for item in missing_in_a:
            result += json.dumps(item, ensure_ascii=False) + '\n'
    if missing_in_b:
        result += f"\nЭлементы, которых нет в отчёте {selected_ids[1]}:\n"
        for item in missing_in_b:
            result += json.dumps(item, ensure_ascii=False) + '\n'

    # Выводим результат в текстовое поле
    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, result)

    # Возвращаем недостающие элементы
    return missing_in_a + missing_in_b

# Диалог выбора файла
def select_database():
    global db_path
    db_path = filedialog.askopenfilename(title="Выберите базу данных", filetypes=(("SQLite files", "*.db *.db3"), ("All Files", "*.*")))
    if db_path:
        load_reports(db_path)
    else:
        messagebox.showwarning("Внимание", "Не выбран файл базы данных.")

# Загрузка отчетов из базы данных
def load_reports(db_path):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("SELECT id, note FROM csoparams")
    reports = cursor.fetchall()
    connection.close()

    # Очищаем старую информацию
    clear_checkboxes()

    # Создаем Scrollbar и Canvas для прокрутки чекбоксов
    canvas = tk.Canvas(report_frame)
    scrollbar = tk.Scrollbar(report_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Создаем чекбоксы для выбора отчетов
    global checkbuttons
    checkbuttons = []  # список для хранения ссылок на чекбоксы
    global var_states  # словарь состояний чекбоксов (id : bool)
    var_states = {}

    for idx, (id_, note_) in enumerate(reports):
        var = tk.BooleanVar()
        chkbtn = tk.Checkbutton(scrollable_frame, text=f"{id_}: {note_}", variable=var)
        chkbtn.grid(row=idx, column=0, sticky='w')
        checkbuttons.append(chkbtn)
        var_states[id_] = var







    # Кнопка для добавления нового элемента
    add_element_btn = tk.Button(scrollable_frame, text="Добавить элемент", command=add_new_element_form)
    add_element_btn.grid(row=len(checkbuttons)+1, column=0, pady=10)
    # Кнопка для удаления элемента
    delete_element_btn = tk.Button(scrollable_frame, text="Удалить элемент", command=delete_element_form)
    delete_element_btn.grid(row=len(checkbuttons)+2, column=0, pady=10)
    # Кнопка для запуска сравнения
    btn_compare = tk.Button(scrollable_frame, text="Сравнить", command=lambda: compare_selected(var_states))
    btn_compare.grid(row=len(checkbuttons), column=0, pady=10)

    # Обновляем размеры канваса при изменении размеров окон
    scrollable_frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

# Очистка чекбоксов
def clear_checkboxes():
    global checkbuttons
    if checkbuttons:
        for widget in checkbuttons:
            widget.destroy()
        checkbuttons.clear()

# Формирование формы для удаления элемента
def delete_element_form():
    form_top_level = tk.Toplevel(root)
    form_top_level.title("Удалить элемент")
    form_top_level.geometry("450x250")

    # Виджет для ввода элемента (увеличенный до трёх строк)
    tk.Label(form_top_level, text="Укажите элемент для удаления:").pack(pady=5)
    element_entry = tk.Text(form_top_level, height=10, width=54)
    element_entry.pack(pady=5)

    # Кнопка для обработки удаления
    submit_btn = tk.Button(form_top_level, text="Удалить", command=lambda: process_delete_element(element_entry.get("1.0", tk.END)))
    submit_btn.pack(pady=10)

# Функция для обработки удаления элемента
def process_delete_element(user_input):
    new_element = user_input.strip()  # очистка от лишних символов
    choose_reports_for_deleting(json.loads(new_element))



# Форма для добавления нового элемента
def add_new_element_form():
    form_top_level = tk.Toplevel(root)
    form_top_level.title("Добавить новый элемент")
    form_top_level.geometry("450x250")

# Виджет для ввода элемента (увеличен до трех строк)
    tk.Label(form_top_level, text="Введите элемент:").pack(pady=5)
    element_entry = tk.Text(form_top_level, height=10, width=54)  # Высота 3 строки, ширина около 50 символов
    element_entry.pack(pady=5)

# Кнопка для отправки формы
    submit_btn = tk.Button(form_top_level, text="Добавить", command=lambda: process_new_element(element_entry.get("1.0", tk.END)))  # Правильно передали аргументы
    submit_btn.pack(pady=10)

# Обрабатываем ввод нового элемента
def process_new_element(element):
    new_element = element.strip()  # очищаем от лишних символов
    choose_reports_for_adding(new_element)

# Выбор отчетов для добавления нового элемента
def choose_reports_for_adding(new_element):
    report_selection_window = tk.Toplevel(root)
    report_selection_window.title("Выбор отчетов для добавления нового элемента")

    # Создаем Scrollbar и Canvas для прокрутки чекбоксов
    canvas = tk.Canvas(report_selection_window)
    scrollbar = tk.Scrollbar(report_selection_window, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Чекбоксы для выбора отчетов
    checkbuttons = []
    for id_ in sorted(var_states.keys()):
        var = tk.BooleanVar()
        chkbtn = tk.Checkbutton(scrollable_frame, text=id_, variable=var)
        chkbtn.pack(pady=5)
        checkbuttons.append((chkbtn, var))

    # Кнопка для подтверждения выбора отчетов
    confirm_btn = tk.Button(scrollable_frame, text="Подтвердить", command=lambda: finalize_addition(new_element, checkbuttons, report_selection_window))
    confirm_btn.pack(pady=10)

    # Обновляем размеры канваса при изменении размеров окон
    scrollable_frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

# Финальное добавление нового элемента в выбранные отчёты
def finalize_addition(new_element, checkbuttons, parent_top_level):
    # Получаем список выбранных отчетов
    selected_reports = [id_ for id_, var in zip([cb[0]['text'] for cb in checkbuttons], [cb[1].get() for cb in checkbuttons]) if var]

    if not selected_reports:
        messagebox.showwarning("Внимание", "Выберите хотя бы один отчёт для добавления элемента.")
        return

    # Добавляем элемент в каждый выбранный отчет
    for report_id in selected_reports:
        add_element_to_report(report_id, new_element)

    # Уничтожаем окно выбора отчетов
    parent_top_level.destroy()

def process_new_element(user_input):
    # Парсим вводимый элемент (если ожидается JSON-структура)
    try:
        new_element = json.loads(user_input)
    except json.JSONDecodeError:
        messagebox.showerror("Ошибка", "Неверный формат данных. Используйте корректный JSON.")
        return

    # Проверяем наличие обязательных полей
    required_fields = ["label", "type"]  # обязательные поля
    if isinstance(new_element, dict):
        if any(field not in new_element for field in required_fields):
            messagebox.showerror("Ошибка", f"Отсутствуют обязательные поля: {', '.join(required_fields)}.")
            return
    elif isinstance(new_element, int):
        messagebox.showerror("Ошибка", "Получены недопустимые данные. Необходимо ввести корректный JSON.")
        return
    else:
        messagebox.showerror("Ошибка", "Неподдерживаемый тип данных.")
        return

    # Далее идет логика добавления элемента...
    choose_reports_for_adding(new_element)



# Добавление элемента в отчет
def add_element_to_report(report_id, element):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Получаем текущие данные отчета
    query = f'SELECT parameter FROM csoparams WHERE id={report_id}'
    cursor.execute(query)
    result = cursor.fetchone()

    if result is None:
        messagebox.showerror("Ошибка", f"Отчёт с ID {report_id} не найден.")
        return

    existing_data = json.loads(result[0])

    # Добавляем новый элемент в конец
    existing_data.append(element)

    # Обновляем данные в базе
    update_query = f'UPDATE csoparams SET parameter=? WHERE id={report_id}'
    cursor.execute(update_query, (json.dumps(existing_data, ensure_ascii=False), ))
    connection.commit()
    connection.close()

    # Сообщаем пользователю о завершении добавления
    show_result_gui(report_id, element)








# Сравнение выбранных отчетов
def compare_selected(var_states):
    selected_ids = [id_ for id_, var in var_states.items() if var.get()]
    if len(selected_ids) != 2:
        messagebox.showwarning("Внимание", "Выберите ровно два отчета для сравнения.")
        return

    # Сравниваем отчеты и получаем недостающие элементы
    missing_elements = compare_reports(selected_ids, db_path)

    # Выводим окно выбора элемента для добавления
    if missing_elements:
        open_add_or_remove_form(missing_elements)

# Окно выбора элемента для добавления или удаления
def open_add_or_remove_form(missing_elements):
    top_level = tk.Toplevel(root)
    top_level.title("Добавить или удалить элемент")
    top_level.geometry("1500x500")  # Зафиксируем размер окна побольше

    # Верхний контейнер для разделения областей
    upper_container = tk.Frame(top_level)
    upper_container.pack(fill=tk.BOTH, expand=True)

    # Нижний контейнер для кнопок
    lower_container = tk.Frame(top_level)
    lower_container.pack(fill=tk.X, side=tk.BOTTOM)

    # Canvas для прокрутки содержимого верхнего контейнера
    canvas = tk.Canvas(upper_container)
    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Полоса прокрутки
    y_scrollbar = tk.Scrollbar(upper_container, orient=tk.VERTICAL, command=canvas.yview)
    y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    canvas.configure(yscrollcommand=y_scrollbar.set)

    # Внутренний фрейм для элементов и Radio-кнопок
    inner_frame = tk.Frame(canvas)
    canvas.create_window((0, 0), window=inner_frame, anchor="nw")

    # Radio-кнопки для выбора элемента
    fields = ['Элемент для действия:', '']
    radio_buttons = []
    choice_var = tk.IntVar()

    for idx, missing in enumerate(missing_elements):
        # Ограничиваем длину строки для вывода
        element_text = json.dumps(missing, ensure_ascii=False)
        
        # Делим текст на две равные части
        half_length = len(element_text) // 1
        first_half = element_text[:half_length]
        second_half = element_text[half_length:]
        
        # Первая строка
        lbl_first = tk.Label(inner_frame, text=first_half, wraplength=1500)
        lbl_first.pack(pady=5)
        
        # Вторая строка
        lbl_second = tk.Label(inner_frame, text=second_half, wraplength=1500)
        lbl_second.pack(pady=5)
        
        # Радио-кнопка
        rb = tk.Radiobutton(inner_frame, text=f"Выбрать элемент №{idx+1}", variable=choice_var, value=idx)
        rb.pack(pady=5)
        radio_buttons.append(rb)

    # Кнопка для добавления (фиксированная внизу)
    add_btn = tk.Button(lower_container, text="Добавить", command=lambda: handle_add_action(missing_elements, choice_var.get(), top_level))
    add_btn.pack(side=tk.LEFT, padx=10, pady=10)

    # Кнопка для удаления (фиксированная внизу)
    delete_btn = tk.Button(lower_container, text="Удалить", command=lambda: handle_delete_action(missing_elements, choice_var.get(), top_level))
    delete_btn.pack(side=tk.LEFT, padx=10, pady=10)




    # Обновляем размеры внутреннего фрейма
    def update_scroll_region(event=None):
        canvas.configure(scrollregion=canvas.bbox("all"))

    inner_frame.bind("<Configure>", update_scroll_region)
    update_scroll_region()

# Обработка добавления элемента
def handle_add_action(missing_elements, index, parent_top_level):
    # Получаем выбранный элемент
    selected_element = missing_elements[index]

    # Уничтожаем текущее окно выбора элемента
    parent_top_level.destroy()

    # Переходим к выбору отчетов
    choose_reports_for_adding(selected_element)

# Обработка удаления элемента
def handle_delete_action(missing_elements, index, parent_top_level):
    # Получаем выбранный элемент
    selected_element = missing_elements[index]

    # Уничтожаем текущее окно выбора элемента
    parent_top_level.destroy()

    # Переходим к выбору отчетов для удаления
    choose_reports_for_deleting(selected_element)

# Выбор отчетов для добавления элемента
def choose_reports_for_adding(selected_element):
    report_selection_window = tk.Toplevel(root)
    report_selection_window.title("Выбор отчетов для добавления")

    # Создаем Scrollbar и Canvas для прокрутки чекбоксов
    canvas = tk.Canvas(report_selection_window)
    scrollbar = tk.Scrollbar(report_selection_window, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Чекбоксы для выбора отчетов
    checkbuttons = []
    for id_ in sorted(var_states.keys()):
        var = tk.BooleanVar()
        chkbtn = tk.Checkbutton(scrollable_frame, text=id_, variable=var)
        chkbtn.pack(pady=5)
        checkbuttons.append((chkbtn, var))

    # Кнопка для подтверждения выбора отчетов
    confirm_btn = tk.Button(scrollable_frame, text="Подтвердить", command=lambda: finalize_addition(selected_element, checkbuttons, report_selection_window))
    confirm_btn.pack(pady=10)

    # Обновляем размеры канваса при изменении размеров окон
    scrollable_frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

# Выбор отчетов для удаления элемента
def choose_reports_for_deleting(selected_element):
    report_selection_window = tk.Toplevel(root)
    report_selection_window.title("Выбор отчетов для удаления")
    report_selection_window.geometry("400x300")  # Установим фиксированные размеры окна

    # Основной контейнер для Scrollbar и Canvas
    main_frame = tk.Frame(report_selection_window)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Прокручиваемый контент
    canvas = tk.Canvas(main_frame)
    scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    # Настройка связей между компонентом прокрутки и контентом
    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    # Чекбоксы для выбора отчетов
    checkbuttons = []
    for id_ in sorted(var_states.keys()):
        var = tk.BooleanVar()
        chkbtn = tk.Checkbutton(scrollable_frame, text=id_, variable=var)
        chkbtn.pack(pady=5)
        checkbuttons.append((chkbtn, var))

    # Кнопка для подтверждения выбора отчетов
    confirm_btn = tk.Button(scrollable_frame, text="Подтвердить", command=lambda: finalize_deletion(selected_element, checkbuttons, report_selection_window))
    confirm_btn.pack(pady=10)

    # Обновляем размеры канваса при изменении размеров окон
    def on_canvas_configure(event):
        canvas.configure(scrollregion=canvas.bbox("all"))
    
    scrollable_frame.bind("<Configure>", on_canvas_configure)

    # Обновляем размеры канваса сразу при открытии окна
    scrollable_frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

# Финальное добавление элемента в выбранные отчёты
def finalize_addition(selected_element, checkbuttons, parent_top_level):
    # Получаем список выбранных отчетов
    selected_reports = [id_ for id_, var in zip([cb[0]['text'] for cb in checkbuttons], [cb[1].get() for cb in checkbuttons]) if var]

    if not selected_reports:
        messagebox.showwarning("Внимание", "Выберите хотя бы один отчет для добавления элемента.")
        return

    # Добавляем элемент в каждый выбранный отчет
    for report_id in selected_reports:
        add_element_to_report(report_id, selected_element)

    # Уничтожаем окно выбора отчетов
    parent_top_level.destroy()

# Финальное удаление элемента из выбранных отчетов
def finalize_deletion(selected_element, checkbuttons, parent_top_level):
    # Получаем список выбранных отчетов
    selected_reports = [id_ for id_, var in zip([cb[0]['text'] for cb in checkbuttons], [cb[1].get() for cb in checkbuttons]) if var]

    if not selected_reports:
        messagebox.showwarning("Внимание", "Выберите хотя бы один отчет для удаления элемента.")
        return

    # Удаляем элемент из каждого выбранного отчета
    for report_id in selected_reports:
        remove_element_from_report(report_id, selected_element)

    # Уничтожаем окно выбора отчетов
    parent_top_level.destroy()

# Добавление элемента в отчет
def add_element_to_report(report_id, element):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Получаем текущие данные отчета
    query = f'SELECT parameter FROM csoparams WHERE id={report_id}'
    cursor.execute(query)
    existing_data = json.loads(cursor.fetchone()[0])

    # Определяем позицию для вставки
    # Ищем ближайший элемент того же типа
    position = next(
        (
            i for i, e in enumerate(existing_data)
            if e.get("type") == element.get("type")
        ),
        None
    )

    # Если позиция найдена, вставляем элемент перед ней
    if position is not None:
        existing_data.insert(position, element)
    else:
        # Если подходящей позиции нет, добавляем элемент в конец
        existing_data.append(element)

    # Обновляем данные в базе
    update_query = f'UPDATE csoparams SET parameter=? WHERE id={report_id}'
    cursor.execute(update_query, (json.dumps(existing_data, ensure_ascii=False), ))
    connection.commit()
    connection.close()

    # Сообщаем пользователю о завершении добавления
    show_result_gui(report_id, element)

def remove_element_from_report(report_id, element):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    # Получаем текущие данные отчета
    query = f'SELECT parameter FROM csoparams WHERE id={report_id}'
    cursor.execute(query)
    result = cursor.fetchone()

    if result is None:
        messagebox.showerror("Ошибка", f"Отчет с ID {report_id} не найден.")
        return

    existing_data = json.loads(result[0])

    # Сначала проверяем, существует ли элемент в отчёте
    if element not in existing_data:
        messagebox.showinfo("Предупреждение", f"Элемент не найден в отчёте с ID {report_id}. Ничего не удалено.")
        return

    # Теперь безопасно удаляем элемент
    existing_data.remove(element)

    # Обновляем данные в базе
    update_query = f'UPDATE csoparams SET parameter=? WHERE id={report_id}'
    cursor.execute(update_query, (json.dumps(existing_data, ensure_ascii=False), ))
    connection.commit()
    connection.close()

    # Сообщаем пользователю о завершении удаления
    show_result_gui(report_id, element)

# Показ результата добавления или удаления
def show_result_gui(report_id, element):
    top_level = tk.Toplevel(root)
    top_level.title("Результат добавления / удаления")

    # Информация о выполненной операции
    info_label = tk.Label(top_level, text=f"Операция успешно проведена в отчёте с ID {report_id}.\n\nДетали элемента:\n{json.dumps(element, ensure_ascii=False)}")
    info_label.pack(pady=10)

    # Кнопка для закрытия окна
    close_btn = tk.Button(top_level, text="Закрыть", command=top_level.destroy)
    close_btn.pack(pady=10)

# Главное окно
root = tk.Tk()
root.title("Выбор базы данных и сравнение отчетов")
# Проверка наличия иконки
app_dir = pathlib.Path(__file__).resolve().parent
icon_path = os.path.join(app_dir, 'osa.ico')
try:
    root.iconbitmap(icon_path)
except Exception as e:
    pass
# Рамка для элементов
frame = tk.Frame(root)
frame.pack(fill=tk.BOTH, expand=True)

# Кнопка для выбора базы данных
select_button = tk.Button(frame, text="Выбрать базу данных", command=select_database)
select_button.pack(pady=10)

# Frame для чекбоксов отчетов
report_frame = tk.Frame(frame)
report_frame.pack(pady=10)

# TextWidget для отображения результатов
result_text = tk.Text(frame, wrap=tk.WORD, height=20, width=60)
result_text.pack(padx=10, pady=10)

# Global variables
db_path = None
checkbuttons = []
reports = None  # храним список отчетов

# Запускаем главную петлю Tkinter
root.mainloop()