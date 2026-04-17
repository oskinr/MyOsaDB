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
            result += json.dumps(item, ensure_ascii=False, separators=(',', ':')) + '\n'
    if missing_in_b:
        result += f"\nЭлементы, которых нет в отчёте {selected_ids[1]}:\n"
        for item in missing_in_b:
            result += json.dumps(item, ensure_ascii=False, separators=(',', ':')) + '\n'

    # Выводим результат в текстовое поле
    result_text.delete(1.0, tk.END)
    result_text.insert(tk.END, result)

    # Возвращаем недостающие элементы
    return missing_in_a + missing_in_b



#Функция редактирования
def update_selected(var_states):
    # 1. Проверяем, что выбран ровно один отчёт
    selected_ids = [id_ for id_, var in var_states.items() if var.get()]
    if len(selected_ids) != 1:
        messagebox.showwarning("Внимание", "Для редактирования нужно выбрать ровно один отчёт.")
        return
    report_id = selected_ids[0]

    if not db_path:
        messagebox.showerror("Ошибка", "Сначала выберите файл базы данных.")
        return

    try:
        # 2. Подключаемся к базе и достаем данные (список объектов)
        connection = sqlite3.connect(db_path)
        cursor = connection.cursor()
        cursor.execute("SELECT parameter FROM csoparams WHERE id = ?", (report_id,))
        result = cursor.fetchone()
        
        if not result:
            messagebox.showerror("Ошибка", f"Отчёт с ID {report_id} не найден в базе.")
            connection.close()
            return

        json_text = result[0]
        connection.close()

       
       # 3. Парсим JSON-текст в список Python
        config_list = json.loads(json_text)

        # --- Начинаем создание окна редактирования ---
        edit_window = tk.Toplevel(root)
        edit_window.title(f"Редактирование отчёта ID: {report_id}")
        try:
            edit_window.iconbitmap(icon_path)
        except Exception:
            pass 
        
        edit_window.grid_rowconfigure(0, weight=1)
        edit_window.grid_columnconfigure(0, weight=1)
        edit_window.geometry("800x600") 
        
        main_frame = ttk.Frame(edit_window)
        main_frame.grid(row=0, column=0, sticky="nsew")

        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)

        widget_data = {}

        # --- ГЛАВНОЕ ИЗМЕНЕНИЕ ---
        # Проходим по ВСЕМ элементам config_list без пропусков по label/type.
        # Если элемент "битый" (нет label/type), мы всё равно создадим для него рамку с текстом ошибки.
        for idx, item in enumerate(config_list):
            # Пытаемся получить данные. Если это не словарь - пропускаем элемент.
            if not isinstance(item, dict):
                print(f"⚠️  Элемент {idx} не является словарём. Пропускаем.")
                continue

            label = item.get("label", f"[Элемент без подписи №{idx}]")
            item_type = item.get("type", "unknown")

            # Создаём фрейм для каждой секции (включая битые элементы)
            section_frame = ttk.Frame(scrollable_frame)
            section_frame.pack(fill="x", pady=5, padx=10)
            
            ttk.Label(section_frame, text=f"{label} (Тип: {item_type})", font=('TkDefaultFont', 9, 'bold')).pack(anchor='w')
            
            inner_frame = ttk.Frame(section_frame)
            inner_frame.pack(fill="x", padx=10, pady=5)


            # 1. Текстовые поля (text_field)
            if item_type == "text_field" and item.get("text_element"):
                text_data = item["text_element"]
                text_var = tk.StringVar(value=text_data.get('value', ''))
                
                ttk.Label(inner_frame, text="Значение:").grid(row=0, column=0, sticky="w")
                
                entry = ttk.Entry(inner_frame, textvariable=text_var, width=50)
                entry.grid(row=0, column=1, sticky="ew", pady=5)
                
                widget_data[label] = {
                    "type": "text_field",
                    "widget": entry,
                    "var": text_var,
                    "name": text_data.get('name')
                }
                inner_frame.grid_columnconfigure(1, weight=1)

            # 2. Выпадающие списки (combo_box)
            elif item_type == "combo_box" and item.get("combo_box_element"):
                combo_options = item["combo_box_element"]
                selected_value = tk.StringVar()
                combo = ttk.Combobox(inner_frame, textvariable=selected_value, state="readonly")
                combo['values'] = [opt.get('text') for opt in combo_options if 'text' in opt]
                
                for opt in combo_options:
                    if opt.get('selected') is True and 'text' in opt:
                        selected_value.set(opt.get('text'))
                        break

                combo.grid(row=0, column=1, sticky="ew", pady=5)
                ttk.Label(inner_frame, text="Выбор:").grid(row=0, column=0, sticky="w")
                
                widget_data[label] = {
                    "type": "combo_box",
                    "widget": combo,
                    "options": combo_options,
                    "var": selected_value
                }
                inner_frame.grid_columnconfigure(1, weight=1)

            # 3. Чекбоксы (checkbox)
            elif item_type == "checkbox" and item.get("checkbox_element"):
                chk_data = item["checkbox_element"]
                bool_var = tk.BooleanVar(value=chk_data.get('checked', False))
                
                chk = ttk.Checkbutton(inner_frame, text="", variable=bool_var)
                chk.grid(row=0, column=0, sticky="w")
                
                ttk.Label(inner_frame, text="Включено:").grid(row=0, column=1, sticky="w")
                
                widget_data[label] = {
                    "type": "checkbox",
                    "widget": chk,
                    "var": bool_var,
                    "name": chk_data.get('name')
                }
            
            # 4. Таблицы (table) - УНИВЕРСАЛЬНЫЙ КОД
            elif item_type == "table" and isinstance(item.get("table_element"), list):
                table_data = item["table_element"]

                # --- Создаем фрейм и скролл для таблицы ---
                table_outer_frame = ttk.Frame(inner_frame)
                table_outer_frame.pack(fill="both", expand=True, pady=5)

                table_canvas = tk.Canvas(table_outer_frame)
                scrollbar = ttk.Scrollbar(table_outer_frame, orient="vertical", command=table_canvas.yview)
                scrollable_inner = ttk.Frame(table_canvas)

# --- НОВОЕ: ОЧИСТКА КОНТЕЙНЕРА ПЕРЕД ОТРИЗОВКОЙ ---
                # Уничтожаем все старые виджеты, которые могли остаться от предыдущей таблицы
                for widget in scrollable_inner.winfo_children():
                    widget.destroy()




                scrollable_inner.bind("<Configure>", lambda e: table_canvas.configure(scrollregion=table_canvas.bbox("all")))
                table_canvas.create_window((0, 0), window=scrollable_inner, anchor="nw")
                table_canvas.configure(yscrollcommand=scrollbar.set)

                table_canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")

                # Словарь для хранения переменных для функции сохранения
                vars_for_saving = {}

                # --- ЦИКЛ ПО ВСЕМ СТРОКАМ ТАБЛИЦЫ ---
                for row_idx, row in enumerate(table_data):
                    if not isinstance(row, dict):
                        continue

                    chk_info = row.get("checkbox", {})
                    value_to_find = chk_info.get("value", "")
                    col1_value = row.get("col1", "")

          

                    # --- ЛОГИКА ДЛЯ ТАБЛИЦЫ "ПОСТАВЩИКОВ" ---
                    if value_to_find:
                        var = tk.BooleanVar(value=chk_info.get("checked", False))
                        chk = ttk.Checkbutton(scrollable_inner, variable=var)
                        chk.grid(row=row_idx, column=0, sticky="w", padx=5, pady=2)

                        ttk.Label(scrollable_inner, text=str(col1_value), anchor="w").grid(
                            row=row_idx, column=1, sticky="we", padx=(0, 5), pady=2
                        )

                        vars_for_saving[value_to_find] = var

                # --- Сохраняем данные для save_all_changes ---
                # Этот блок теперь ВНЕ цикла for, чтобы сохранить результат для ВСЕЙ таблицы.
                widget_data[label] = {
                    "type": "table",
                    "vars": vars_for_saving,
                    "original_data": table_data,
                    "label": label,
                }

            #  # --- Блок для "битых" элементов или неизвестных типов ---
            # else:
            #      # Если мы дошли сюда, значит тип элемента неизвестен или структура сломана.
            #      # Покажем сообщение об этом прямо в интерфейсе.
            #     error_text = f"Неизвестный тип '{item_type}' или повреждённая структура данных."
            #     if not label or label == "[Элемент без подписи]":
            #          error_text += "\n(У элемента отсутствует поле 'label')"
            #     if not item_type or item_type == "unknown":
            #          error_text += "\n(У элемента отсутствует поле 'type')"
                     
            #     ttk.Label(inner_frame, text=f"⚠️ {error_text}", foreground="red").pack(anchor='w')

            #   # Конец цикла FOR по элементам


        def save_all_changes():
            # Проходим по собранным данным и обновляем структуру config_list
            for item in config_list:
                label = item.get("label")
                data = widget_data.get(label)
                if not data:
                    continue

                if data["type"] == "text_field":
                    new_value = data["var"].get()
                    if data["name"] and "text_element" in item:
                        item["text_element"]["value"] = new_value

                elif data["type"] == "combo_box":
                    new_text = data["var"].get()
                    for option in data["options"]:
                        option['selected'] = False
                        if option.get('text') == new_text:
                            option['selected'] = True

                elif data["type"] == "checkbox":
                    new_state = data["var"].get()
                    if data["name"] and "checkbox_element" in item:
                        item["checkbox_element"]["checked"] = new_state

                elif data["type"] == "table":
                    # data["vars"] - это словарь вида: {value_to_find: BooleanVar}
                    for value_to_find, var in data["vars"].items():
                        new_state = var.get()
                        
                        # Ищем в исходных данных строку/элемент, у которого checkbox.value совпадает с ключом словаря
                        for row in data["original_data"]:
                            if isinstance(row.get("checkbox"), dict):
                                if row["checkbox"].get("value") == value_to_find:
                                    row["checkbox"]["checked"] = new_state
                                    break  # Выходим из цикла по строкам, так как нашли нужную

            # Запись в БД
            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Обновляем весь список параметров для отчёта.
                # ensure_ascii=False для русских букв.
                cursor.execute(
                    "UPDATE csoparams SET parameter = ? WHERE id = ?",
                    (json.dumps(config_list, ensure_ascii=False, separators=(',', ':')), report_id)
                )
                
                conn.commit()
                conn.close()
                
                messagebox.showinfo("Успех", "Все изменения сохранены!")
                edit_window.destroy() # Закрываем окно после сохранения

            except Exception as e:
                messagebox.showerror("Ошибка БД", f"Не удалось сохранить данные: {e}")


        save_btn = ttk.Button(scrollable_frame, text="Сохранить все изменения", command=save_all_changes)
        save_btn.pack(pady=20) 

    except json.JSONDecodeError:
        messagebox.showerror("Ошибка JSON", "Данные из базы повреждены.")
    except sqlite3.Error as e:
        messagebox.showerror("Ошибка БД", f"Ошибка подключения: {e}")
    except Exception as e:
        messagebox.showerror("Критическая ошибка", f"Произошла ошибка: {e}")






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





   # Кнопка для запуска сравнения
    btn_compare = tk.Button(scrollable_frame, text="Сравнить", command=lambda: compare_selected(var_states))
    btn_compare.grid(row=len(checkbuttons), column=0, pady=10)

    # Кнопка для добавления нового элемента
    add_element_btn = tk.Button(scrollable_frame, text="Добавить элемент", command=add_new_element_form)
    add_element_btn.grid(row=len(checkbuttons)+1, column=0, pady=10)
    # Кнопка для удаления элемента
    delete_element_btn = tk.Button(scrollable_frame, text="Удалить элемент", command=delete_element_form)
    delete_element_btn.grid(row=len(checkbuttons)+2, column=0, pady=10)
    # Новая кнопка для удаления отчета
    delete_report_btn = tk.Button(scrollable_frame, text="Удалить отчет", command=delete_reports)
    delete_report_btn.grid(row=len(checkbuttons)+3, column=0, pady=10)
    
    # Кнопка для редактирования
    btn_compare = tk.Button(scrollable_frame, text="Редактировать отчет", command=lambda: update_selected(var_states))
    btn_compare.grid(row=len(checkbuttons)+4, column=0, pady=10)

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


# Функция для физического удаления отчетов
def delete_reports():
    selected_reports = [id_ for id_, var in var_states.items() if var.get()]
    if not selected_reports:
        messagebox.showwarning("Внимание", "Выберите хотя бы один отчет для удаления.")
        return

    confirmation = messagebox.askyesno("Подтверждение", f"Удалить {len(selected_reports)} отчетов навсегда?")
    if not confirmation:
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    for report_id in selected_reports:
        cursor.execute("DELETE FROM csoparams WHERE id=?", (report_id,))

    conn.commit()
    conn.close()

    messagebox.showinfo("Готово", f"Удалено {len(selected_reports)} отчетов.")


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
# Глобальная переменная для хранения выбора из ComboBox
# Должна быть объявлена в самом начале файла, рядом с другими глобальными переменными
# global metka 
# Но лучше объявить ее здесь при первом использовании в функции

def add_new_element_form():
    global metka # Объявляем, что будем работать с глобальной переменной

    form_top_level = tk.Toplevel(root)
    form_top_level.title("Добавить новый элемент")
    form_top_level.geometry("450x300")

    # Виджет для ввода элемента
    tk.Label(form_top_level, text="Введите элемент (JSON):").pack(pady=5)
    element_entry = tk.Text(form_top_level, height=10, width=54)
    element_entry.pack(pady=5)

    # --- Блок с Combobox ---
    frame_combo = tk.Frame(form_top_level)
    frame_combo.pack(pady=5)

    tk.Label(frame_combo, text="Вставить после:").pack(side="left")
    combo_type = ttk.Combobox(frame_combo, values=["Период", "Район","Исключая поставщиков" ], state="readonly", width=10)
    combo_type.pack(side="left", padx=5)
    combo_type.current(0) # Устанавливаем "Период" по умолчанию

    # Инициализируем глобальную переменную
    metka = combo_type.get() 

    def update_metka(event):
        global metka # Обязательно используем global внутри функции для изменения
        metka = event.widget.get()
        messagebox.showinfo('Внимание',f'Элемент будет вставлен после строки: {metka}')

    combo_type.bind("<<ComboboxSelected>>", update_metka)
    # --- Конец блока с Combobox ---


    # Кнопка для отправки формы
    submit_btn = tk.Button(form_top_level, text="Добавить", command=lambda: process_new_element(element_entry.get("1.0", tk.END)))
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
def finalize_addition(selected_element, checkbuttons, parent_top_level):
    # Получаем список выбранных отчетов
    selected_reports = [id_ for id_, var in zip([cb[0]['text'] for cb in checkbuttons], [cb[1].get() for cb in checkbuttons]) if var]

    if not selected_reports:
        messagebox.showwarning("Внимание", "Выберите хотя бы один отчёт для добавления элемента.")
        return

    # Добавляем элемент в каждый выбранный отчет, передавая позицию вставки (metka)
    for report_id in selected_reports:
        add_element_to_report(report_id, selected_element, insert_before=metka)

    # Уничтожаем окно выбора отчетов
    parent_top_level.destroy()

def process_new_element(user_input):
    # Парсим вводимый элемент (если ожидается JSON-структура)
    try:
        new_element = json.loads(user_input)
    except json.JSONDecodeError:
        messagebox.showerror("Ошибка", "Неверный формат данных. Используйте корректный JSON.")
        return

    # # Проверяем наличие обязательных полей
    # required_fields = ["label", "type"]  # обязательные поля
    # if isinstance(new_element, dict):
    #     if any(field not in new_element for field in required_fields):
    #         messagebox.showerror("Ошибка", f"Отсутствуют обязательные поля: {', '.join(required_fields)}.")
    #         return
    # elif isinstance(new_element, int):
    #     messagebox.showerror("Ошибка", "Получены недопустимые данные. Необходимо ввести корректный JSON.")
    #     return
    # else:
    #     messagebox.showerror("Ошибка", "Неподдерживаемый тип данных.")
    #     return

    # Далее идет логика добавления элемента...
    choose_reports_for_adding(new_element)



# Добавление элемента в отчет







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
        element_text = json.dumps(missing, ensure_ascii=False, separators=(',', ':'))
        
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
        messagebox.showwarning("Внимание", "Выберите хотя бы один отчёт для добавления элемента.")
        return

    # Добавляем элемент в каждый выбранный отчет, передавая позицию вставки
    for report_id in selected_reports:
        add_element_to_report(report_id, selected_element, insert_before=metka)

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
def add_element_to_report(report_id, element, insert_before=None):
    """
    Добавляет или вставляет элемент в отчет.
    Логика для "Исключая поставщиков" изменена: 
    новый поставщик вставляется в таблицу по алфавиту.
    """
    if not db_path:
        messagebox.showerror("Ошибка", "Путь к базе данных не задан.")
        return

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT parameter FROM csoparams WHERE id = ?", (report_id,))
        result = cursor.fetchone()

        if not result:
            messagebox.showerror("Ошибка", f"Отчёт с ID {report_id} не найден.")
            return

        config_list = json.loads(result[0])
        element_added = False

        # Проходим по всему списку элементов отчёта
        for i in range(len(config_list)):
            current_item = config_list[i]
            current_label = current_item.get('label')
            current_type = current_item.get('type')

            # --- ЛОГИКА ДЛЯ ТАБЛИЦЫ "ИСКЛЮЧАЯ ПОСТАВЩИКОВ" (ИСПРАВЛЕННАЯ) ---
            if metka == "Исключая поставщиков":
                # Проверяем, что текущий элемент - это нужный заголовок
                is_correct_title = (
                    current_type == 'table_title' and
                    current_label == 'Исключая поставщиков'
                )
                
                # Проверяем, что СЛЕДУЮЩИЙ элемент - это таблица
                if is_correct_title and i + 1 < len(config_list):
                    next_item = config_list[i + 1]
                    is_valid_table = (
                        next_item.get('type') == 'table' and
                        isinstance(next_item.get('table_element'), list)
                    )
                    
                    if is_valid_table:
                        # Получаем данные таблицы и заголовок
                        table_data = next_item['table_element']
                        header = table_data[0]  # Первая строка - это заголовок

                        # --- АЛФАВИТНАЯ ВСТАВКА ---
                        # Находим позицию для вставки (по col1)
                        insert_position = len(table_data)  # По умолчанию - в конец
                        
                        # Начинаем с 1, чтобы пропустить заголовок (строка 0)
                        for idx, row in enumerate(table_data[1:], start=1):
                            # Сравниваем названия поставщиков без учета регистра
                            current_name = str(row.get('col1', '')).upper()
                            new_name = str(element.get('col1', '')).upper()
                            
                            if new_name < current_name:
                                insert_position = idx
                                break

                        # Вставляем элемент в найденную позицию
                        table_data.insert(insert_position, element)
                        
                        element_added = True
                        break # Выходим из цикла, так как элемент добавлен

            # --- ЛОГИКА ДЛЯ "ПЕРИОД" И "РАЙОН" (без изменений) ---
            elif metka in ["Период", "Район"]:
                is_target_field = (
                    current_type == 'text_field' and
                    current_label == metka
                )
                if is_target_field:
                    config_list.insert(i + 1, element)
                    element_added = True
                    break

        # --- СТАНДАРТНОЕ ДОБАВЛЕНИЕ В КОНЕЦ (если не нашли метку) ---
        if not element_added and metka not in ["Период", "Район", "Исключая поставщиков"]:
            config_list.append(element)
            element_added = True

        if element_added:
            cursor.execute(
                "UPDATE csoparams SET parameter = ? WHERE id = ?",
                (json.dumps(config_list, ensure_ascii=False), report_id)
            )
            connection.commit()
            messagebox.showinfo("Успех", f"Элемент добавлен в раздел '{metka}'!")
        else:
            messagebox.showerror("Ошибка", f"Раздел '{metka}' не найден в отчёте.")

    except json.JSONDecodeError:
        messagebox.showerror("Ошибка", "Данные в базе повреждены (ошибка JSON).")
    except Exception as e:
        messagebox.showerror("Критическая ошибка", f"Произошла ошибка: {e}")
    finally:
        connection.close()

def remove_element_from_report(report_id, element_to_find):
    """
    Рекурсивно ищет и удаляет элемент из структуры данных отчета.
    Работает как для элементов верхнего уровня, так и для строк внутри таблиц.
    """
    if not db_path:
        messagebox.showerror("Ошибка", "Путь к базе данных не задан.")
        return

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()

    try:
        cursor.execute("SELECT parameter FROM csoparams WHERE id = ?", (report_id,))
        result = cursor.fetchone()

        if not result:
            messagebox.showerror("Ошибка", f"Отчёт с ID {report_id} не найден.")
            return

        config_list = json.loads(result[0])
        element_removed = False

        # --- НОВАЯ ЛОГИКА: Рекурсивный обход ---
        def recursive_remove(obj):
            """
            Эта внутренняя функция ищет элемент для удаления.
            Если объект - это список, она пытается удалить элемент напрямую.
            Если объект - это словарь, она проверяет ключ 'table_element'.
            """
            nonlocal element_removed

            # Если мы нашли список (например, главный список или table_element)
            if isinstance(obj, list):
                # Создаем копию списка для безопасного итерирования
                for i, item in enumerate(obj[:]): 
                    # Если элемент в списке совпадает с тем, что мы ищем
                    if item == element_to_find:
                        obj.remove(item)
                        element_removed = True
                        # Не возвращаемся, так как в списке могут быть дубликаты
                    else:
                        # Если не нашли, идем глубже в текущий элемент
                        recursive_remove(item)

            # Если мы нашли словарь (например, описание виджета или таблицы)
            elif isinstance(obj, dict):
                # Проверяем, есть ли у словаря ключ 'table_element'
                if 'table_element' in obj and isinstance(obj['table_element'], list):
                    # Рекурсивно обрабатываем содержимое таблицы
                    recursive_remove(obj['table_element'])
                else:
                    # Обрабатываем все значения в словаре
                    for key in obj:
                        recursive_remove(obj[key])

        # Запускаем рекурсивный обход с самого верха структуры данных
        recursive_remove(config_list)

        # --- ЗАВЕРШЕНИЕ ---
        if element_removed:
            cursor.execute(
                "UPDATE csoparams SET parameter = ? WHERE id = ?",
                (json.dumps(config_list, ensure_ascii=False), report_id)
            )
            connection.commit()
            messagebox.showinfo("Успех", "Элемент успешно удален.")
        else:
            messagebox.showinfo("Информация", "Элемент не найден в отчёте.")

    except json.JSONDecodeError:
        messagebox.showerror("Ошибка", "Данные в базе повреждены (ошибка JSON).")
    except Exception as e:
        messagebox.showerror("Критическая ошибка", f"Произошла ошибка: {e}")
    finally:
        connection.close()

# Показ результата добавления или удаления
def show_result_gui(report_id, element):
    top_level = tk.Toplevel(root)
    top_level.title("Результат добавления / удаления")

    # Информация о выполненной операции
    info_label = tk.Label(top_level, text=f"Операция успешно проведена в отчёте с ID {report_id}.\n\nДетали элемента:\n{json.dumps(element, ensure_ascii=False, separators=(',', ':'))}")
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