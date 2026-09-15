import customtkinter as ctk
import sqlite3
import json
import copy
from tkinter import filedialog, messagebox
import tkinter as tk
import pathlib
import os

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("blue")


def activate_window(window):
    """Поднимает окно на передний план и даёт ему фокус."""
    window.deiconify()
    window.lift()
    window.focus_force()
    window.after(100, window.lift)
    window.attributes("-topmost", True)
    window.after(150, lambda: window.attributes("-topmost", False))


def checked_copy(row, state):
    """Возвращает копию элемента со значением checkbox.checked = state."""
    new_row = copy.deepcopy(row)
    chk = new_row.get("checkbox")
    if isinstance(chk, dict):
        chk["checked"] = bool(state)
    return new_row


def create_select_checkbox(parent, text, variable):
    """Чекбокс с подсветкой при выборе."""
    chk = ctk.CTkCheckBox(parent, text=text, variable=variable,
                          onvalue=True, offvalue=False)
    base_fg = chk.cget("fg_color")
    base_border = chk.cget("border_color")
    base_text = chk.cget("text_color")
    base_font = chk.cget("font")

    def on_toggle(*args):
        if variable.get():
            chk.configure(fg_color="#3d85c6", border_color="#3d85c6",
                          text_color="#3d85c6", font=('TkDefaultFont', 10, 'bold'))
        else:
            chk.configure(fg_color=base_fg, border_color=base_border,
                          text_color=base_text, font=base_font)

    variable.trace_add('write', on_toggle)
    on_toggle()
    return chk


def fetch_data(cursor, selected_ids):
    query = f'SELECT id, parameter FROM csoparams WHERE id IN ({", ".join(map(str, selected_ids))})'
    cursor.execute(query)
    rows = cursor.fetchall()
    return {row[0]: json.loads(row[1]) for row in rows}


def find_missing_items(list1, list2):
    return [item for item in list1 if item not in list2]


def compare_reports(selected_ids, db_path):
    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    data_by_id = fetch_data(cursor, selected_ids)
    connection.close()

    data_a = data_by_id.get(selected_ids[0], [])
    data_b = data_by_id.get(selected_ids[1], [])

    missing_in_a = find_missing_items(data_b, data_a)
    missing_in_b = find_missing_items(data_a, data_b)

    result = ""
    if missing_in_a:
        result += f"Элементы, которых нет в отчёте {selected_ids[0]}:\n"
        for item in missing_in_a:
            result += json.dumps(item, ensure_ascii=False, separators=(',', ':')) + '\n'
    if missing_in_b:
        result += f"\nЭлементы, которых нет в отчёте {selected_ids[1]}:\n"
        for item in missing_in_b:
            result += json.dumps(item, ensure_ascii=False, separators=(',', ':')) + '\n'

    result_text.delete("1.0", "end")
    result_text.insert("end", result)

    if result:
        result_text.pack(fill="x", padx=5, pady=(0, 5))
    else:
        result_text.pack_forget()

    return missing_in_a + missing_in_b


class EditableTableWidget:
    def __init__(self, parent_frame, table_data, master_var):
        self.parent_frame = parent_frame
        self.table_data = table_data
        self.master_var = master_var
        self.vars_for_saving = {}
        self.json_value_to_uid = {}
        self.scrollable_inner = None
        self._create_widgets()

    def _create_widgets(self):
        for widget in self.parent_frame.winfo_children():
            widget.destroy()

        self.scrollable_inner = ctk.CTkScrollableFrame(self.parent_frame)
        self.scrollable_inner.pack(fill="both", expand=True, pady=5)

        self.vars_for_saving.clear()
        self.json_value_to_uid.clear()

        data_row_counter = 1

        for row_idx, row in enumerate(self.table_data):
            if not isinstance(row, dict):
                continue

            chk_info = row.get("checkbox", {})
            value_to_find = chk_info.get("value", "")

            if row_idx == 0:
                def on_master_check():
                    state = self.master_var.get()
                    for var in self.vars_for_saving.values():
                        var.set(state)

                chk_all = ctk.CTkCheckBox(
                    self.scrollable_inner,
                    text="",
                    variable=self.master_var,
                    onvalue=True,
                    offvalue=False,
                    command=on_master_check
                )
                chk_all.grid(row=0, column=0, sticky="w", padx=(5, 0), pady=2)

                for col_num, key in enumerate(['col1', 'col2', 'col3'], start=1):
                    if key in row and row[key]:
                        lbl = ctk.CTkLabel(
                            self.scrollable_inner,
                            text=str(row[key]),
                            anchor="w",
                            font=('TkDefaultFont', 10, 'bold')
                        )
                        lbl.grid(row=0, column=col_num, sticky="we",
                                 padx=(5 if col_num > 1 else 0, 5), pady=2)
                        self.scrollable_inner.grid_columnconfigure(col_num, weight=1)
                continue

            if value_to_find:
                var = tk.BooleanVar(value=chk_info.get("checked", False))
                rowid = data_row_counter
                self.json_value_to_uid[value_to_find] = rowid

                var.trace_add('write', lambda *args,
                    m_var=self.master_var,
                    save_dict=self.vars_for_saving,
                    current_var=var:
                        m_var.set(all(v.get() for v in save_dict.values() if v is not current_var))
                )

                chk = ctk.CTkCheckBox(self.scrollable_inner, text="", variable=var,
                                       onvalue=True, offvalue=False)
                chk.grid(row=data_row_counter, column=0, sticky="w", padx=(5, 0), pady=2)

                for col_num, key in enumerate(['col1', 'col2', 'col3'], start=1):
                    cell_value = str(row[key]) if key in row and row[key] is not None else ""
                    lbl = ctk.CTkLabel(self.scrollable_inner, text=cell_value, anchor="w")
                    lbl.grid(row=data_row_counter, column=col_num, sticky="we",
                             padx=(5 if col_num > 1 else 0, 5), pady=2)

                self.vars_for_saving[rowid] = var
                data_row_counter += 1

    def get_vars(self):
        return self.vars_for_saving

    def get_value_to_uid_map(self):
        return self.json_value_to_uid

    def get_original_data(self):
        return self.table_data

    def update_data(self, new_table_data):
        self.table_data = new_table_data
        self._create_widgets()

    def destroy(self):
        for widget in self.parent_frame.winfo_children():
            widget.destroy()


def collect_table_sections(config_list):
    sections = []
    pending_title = None
    for item in config_list:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        if item_type == "table_title":
            pending_title = str(item.get("label", ""))
            continue
        if item_type == "table" and isinstance(item.get("table_element"), list):
            label = str(item.get("label") or pending_title or "Таблица")
            rows = [
                row for row in item["table_element"]
                if isinstance(row, dict) and row.get("checkbox", {}).get("value")
            ]
            sections.append({"label": label, "rows": rows})
            pending_title = None
    return sections


def insert_element_into_table(report_id, table_label, element):
    if not db_path:
        messagebox.showerror("Ошибка", "Путь к базе данных не задан.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT parameter FROM csoparams WHERE id = ?", (report_id,))
        result = cursor.fetchone()
        if not result:
            messagebox.showerror("Ошибка", f"Отчёт с ID {report_id} не найден.")
            return

        config_list = json.loads(result[0])
        pending_title = None
        element_added = False

        for i, item in enumerate(config_list):
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")

            if item_type == "table_title":
                pending_title = str(item.get("label", ""))
                continue

            if item_type == "table" and isinstance(item.get("table_element"), list):
                label = str(item.get("label") or pending_title or "")
                if label.lower() != table_label.lower():
                    pending_title = None
                    continue

                table_data = item["table_element"]
                new_name = str(element.get("col1", "")).upper()
                insert_pos = len(table_data)

                for idx, row in enumerate(table_data[1:], start=1):
                    current_name = str(row.get("col1", "")).upper()
                    if new_name < current_name:
                        insert_pos = idx
                        break

                table_data.insert(insert_pos, element)
                element_added = True
                break

        if element_added:
            cursor.execute(
                "UPDATE csoparams SET parameter = ? WHERE id = ?",
                (json.dumps(config_list, ensure_ascii=False, separators=(',', ':')), report_id)
            )
            conn.commit()
        else:
            messagebox.showwarning("Внимание", f"Раздел '{table_label}' не найден в отчёте {report_id}.")

    except json.JSONDecodeError:
        messagebox.showerror("Ошибка", "Данные в базе повреждены (ошибка JSON).")
    except Exception as e:
        messagebox.showerror("Критическая ошибка", f"Произошла ошибка: {e}")
    finally:
        conn.close()


def choose_reports_for_element_insertion(elements, table_label):
    window = ctk.CTkToplevel(root)
    window.title("Выбор отчётов для добавления элемента")
    window.geometry("400x450")

    ctk.CTkLabel(window, text=f"Элемент будет добавлен в раздел: {table_label}",
                 anchor="w", wraplength=360).pack(fill="x", padx=10, pady=(10, 0))

    scroll = ctk.CTkScrollableFrame(window)
    scroll.pack(fill="both", expand=True, padx=10, pady=10)

    checkbuttons = []
    for id_ in sorted(var_states.keys()):
        var = tk.BooleanVar()
        chkbtn = create_select_checkbox(scroll, str(id_), var)
        chkbtn.pack(anchor="w", pady=3)
        checkbuttons.append((chkbtn, var))

    def confirm():
        selected_reports = [
            int(cb[0].cget("text")) for cb in checkbuttons if cb[1].get()
        ]
        if not selected_reports:
            messagebox.showwarning("Внимание", "Выберите хотя бы один отчёт.")
            return
        for report_id in selected_reports:
            for element in elements:
                insert_element_into_table(report_id, table_label, element)
        messagebox.showinfo("Готово",
                            f"Элемент(ы) добавлены в {len(selected_reports)} отчёт(ов).")
        window.destroy()

    ctk.CTkButton(scroll, text="Подтвердить", command=confirm).pack(pady=10)
    activate_window(window)


def remove_element_from_table(report_id, table_label, element):
    if not db_path:
        messagebox.showerror("Ошибка", "Путь к базе данных не задан.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT parameter FROM csoparams WHERE id = ?", (report_id,))
        result = cursor.fetchone()
        if not result:
            messagebox.showerror("Ошибка", f"Отчёт с ID {report_id} не найден.")
            return

        config_list = json.loads(result[0])
        pending_title = None
        element_removed = False
        target_value = element.get("checkbox", {}).get("value")

        for item in config_list:
            if not isinstance(item, dict):
                continue
            item_type = item.get("type")

            if item_type == "table_title":
                pending_title = str(item.get("label", ""))
                continue

            if item_type == "table" and isinstance(item.get("table_element"), list):
                label = str(item.get("label") or pending_title or "")
                if label.lower() != table_label.lower():
                    pending_title = None
                    continue

                table_data = item["table_element"]
                remaining_rows = []
                for row in table_data:
                    if (isinstance(row, dict)
                            and row.get("checkbox", {}).get("value") == target_value):
                        element_removed = True
                    else:
                        remaining_rows.append(row)
                item["table_element"] = remaining_rows
                break

        if element_removed:
            cursor.execute(
                "UPDATE csoparams SET parameter = ? WHERE id = ?",
                (json.dumps(config_list, ensure_ascii=False, separators=(',', ':')), report_id)
            )
            conn.commit()
        else:
            messagebox.showinfo("Информация",
                                f"Элемент не найден в разделе '{table_label}' отчёта {report_id}.")

    except json.JSONDecodeError:
        messagebox.showerror("Ошибка", "Данные в базе повреждены (ошибка JSON).")
    except Exception as e:
        messagebox.showerror("Критическая ошибка", f"Произошла ошибка: {e}")
    finally:
        conn.close()


def choose_reports_for_element_removal(elements, table_label):
    window = ctk.CTkToplevel(root)
    window.title("Выбор отчётов для удаления элемента")
    window.geometry("400x450")

    ctk.CTkLabel(window, text=f"Элемент будет удалён из раздела: {table_label}",
                 anchor="w", wraplength=360).pack(fill="x", padx=10, pady=(10, 0))

    scroll = ctk.CTkScrollableFrame(window)
    scroll.pack(fill="both", expand=True, padx=10, pady=10)

    checkbuttons = []
    for id_ in sorted(var_states.keys()):
        var = tk.BooleanVar()
        chkbtn = create_select_checkbox(scroll, str(id_), var)
        chkbtn.pack(anchor="w", pady=3)
        checkbuttons.append((chkbtn, var))

    def confirm():
        selected_reports = [
            int(cb[0].cget("text")) for cb in checkbuttons if cb[1].get()
        ]
        if not selected_reports:
            messagebox.showwarning("Внимание", "Выберите хотя бы один отчёт.")
            return
        for report_id in selected_reports:
            for element in elements:
                remove_element_from_table(report_id, table_label, element)
        messagebox.showinfo("Готово",
                            f"Элемент(ы) удалены из {len(selected_reports)} отчёт(ов).")
        window.destroy()

    ctk.CTkButton(scroll, text="Подтвердить", command=confirm).pack(pady=10)
    activate_window(window)


def open_select_element_form(config_list):
    sections = [s for s in collect_table_sections(config_list) if s["rows"]]
    if not sections:
        messagebox.showwarning("Внимание", "В отчёте нет табличных элементов для выбора.")
        return

    select_window = ctk.CTkToplevel(root)
    select_window.title("Выбрать элемент")
    select_window.geometry("700x500")
    try:
        select_window.iconbitmap(icon_path)
    except Exception:
        pass

    unique_section_names = []
    seen_labels = set()
    for section in sections:
        if section["label"] not in seen_labels:
            seen_labels.add(section["label"])
            unique_section_names.append(section["label"])

    combo_var = tk.StringVar()
    vars_list = []
    master_var = tk.BooleanVar()

    def on_section_change(value):
        for widget in list_frame.winfo_children():
            widget.destroy()
        vars_list.clear()
        for section in sections:
            if section["label"] != value:
                continue
            for row in section["rows"]:
                select_var = tk.BooleanVar()
                json_var = tk.BooleanVar(value=bool(row.get("checkbox", {}).get("checked", False)))

                select_var.trace_add(
                    'write',
                    lambda *args, m_var=master_var, v_list=vars_list, cur=select_var:
                        m_var.set(all(sv.get() for sv, _, _ in v_list if sv is not cur))
                )

                main_text = str(row.get("col1", ""))
                parts = [str(row.get(key, "")) for key in ("col2", "col3") if row.get(key)]
                if parts:
                    text = f"{main_text} | {' | '.join(parts)}"
                elif main_text:
                    text = main_text
                else:
                    text = json.dumps(row, ensure_ascii=False)

                row_frame = ctk.CTkFrame(list_frame, fg_color="transparent")
                row_frame.pack(fill="x", pady=1, padx=5)

                json_chk = ctk.CTkCheckBox(row_frame, text="", variable=json_var,
                                           onvalue=True, offvalue=False, width=30)
                json_chk.pack(side="left", padx=(5, 2))

                elem_lbl = ctk.CTkLabel(row_frame, text=text, anchor="w", cursor="hand2")
                base_fg = elem_lbl.cget("text_color")
                base_font = elem_lbl.cget("font")

                def _make_highlighter(lbl, fg, font, sv):
                    def _on_change(*args):
                        if sv.get():
                            lbl.configure(text_color="#3d85c6", font=('TkDefaultFont', 10, 'bold'))
                        else:
                            lbl.configure(text_color=fg, font=font)
                    sv.trace_add('write', _on_change)
                    return _on_change

                _make_highlighter(elem_lbl, base_fg, base_font, select_var)
                elem_lbl.bind("<Button-1>", lambda e, sv=select_var: sv.set(not sv.get()))
                elem_lbl.pack(side="left", fill="x", expand=True, anchor="w")

                vars_list.append((select_var, json_var, row))
            break
        master_var.set(False)

    def copy_selected():
        selected_rows = [checked_copy(row, jv.get()) for sv, jv, row in vars_list if sv.get()]
        if not selected_rows:
            messagebox.showwarning("Внимание", "Выберите хотя бы один элемент.")
            return
        text = "\n".join(
            json.dumps(row, ensure_ascii=False, separators=(",", ":"))
            for row in selected_rows
        )
        select_window.clipboard_clear()
        select_window.clipboard_append(text)
        messagebox.showinfo("Готово", "Элемент скопирован в буфер обмена.")

    def add_selected_to_reports():
        selected_rows = [checked_copy(row, jv.get()) for sv, jv, row in vars_list if sv.get()]
        if not selected_rows:
            messagebox.showwarning("Внимание", "Выберите хотя бы один элемент.")
            return
        current_section = combo_var.get()
        choose_reports_for_element_insertion(selected_rows, current_section)

    def remove_selected_from_reports():
        selected_rows = [checked_copy(row, jv.get()) for sv, jv, row in vars_list if sv.get()]
        if not selected_rows:
            messagebox.showwarning("Внимание", "Выберите хотя бы один элемент.")
            return
        current_section = combo_var.get()
        choose_reports_for_element_removal(selected_rows, current_section)

    top_bar = ctk.CTkFrame(select_window, fg_color="transparent")
    top_bar.pack(fill="x", padx=10, pady=10)

    ctk.CTkLabel(top_bar, text="Раздел:").pack(side="left", padx=(0, 5))
    combo = ctk.CTkComboBox(top_bar, values=unique_section_names,
                            variable=combo_var, command=on_section_change, width=280)
    combo.pack(side="left")

    master_row = ctk.CTkFrame(select_window, fg_color="transparent")
    master_row.pack(fill="x", padx=10, pady=(0, 5))

    def on_master_toggle():
        state = master_var.get()
        for sv, _, _ in vars_list:
            sv.set(state)

    master_chk = ctk.CTkCheckBox(master_row, text="Выбрать все элементы, нажмите или отожмите чекбоксы,так как хотите добавлять",
                                  variable=master_var, onvalue=True, offvalue=False,
                                  command=on_master_toggle)
    master_chk.pack(anchor="w")

    list_frame = ctk.CTkScrollableFrame(select_window)
    list_frame.pack(fill="both", expand=True, padx=10, pady=10)

    bottom_bar = ctk.CTkFrame(select_window, fg_color="transparent")
    bottom_bar.pack(fill="x", padx=10, pady=(0, 10))

    save_element_btn = ctk.CTkButton(bottom_bar, text="Сохранить элемент",
                                     command=copy_selected)
    save_element_btn.pack(side="left", padx=(0, 5))

    add_element_btn = ctk.CTkButton(bottom_bar, text="Добавить элемент",
                                    command=add_selected_to_reports)
    add_element_btn.pack(side="left", padx=(0, 5))

    remove_element_btn = ctk.CTkButton(bottom_bar, text="Удалить элемент",
                                       command=remove_selected_from_reports,
                                       fg_color="#c0392b", hover_color="#e74c3c")
    remove_element_btn.pack(side="left")

    combo.set(unique_section_names[0])
    on_section_change(combo.get())
    activate_window(select_window)


def update_selected(var_states):
    selected_ids = [id_ for id_, var in var_states.items() if var.get()]
    if len(selected_ids) != 1:
        messagebox.showwarning("Внимание", "Для редактирования нужно выбрать ровно один отчёт.")
        return
    report_id = selected_ids[0]

    if not db_path:
        messagebox.showerror("Ошибка", "Сначала выберите файл базы данных.")
        return

    try:
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

        config_list = json.loads(json_text)

        edit_window = ctk.CTkToplevel(root)
        edit_window.title(f"Редактирование отчёта ID: {report_id}")
        try:
            edit_window.iconbitmap(icon_path)
        except Exception:
            pass

        edit_window.grid_rowconfigure(0, weight=1)
        edit_window.grid_columnconfigure(0, weight=1)
        edit_window.geometry("800x600")

        main_frame = ctk.CTkFrame(edit_window, fg_color="transparent")
        main_frame.grid(row=0, column=0, sticky="nsew")
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_rowconfigure(1, weight=0)
        main_frame.grid_columnconfigure(0, weight=1)

        scrollable_frame = ctk.CTkScrollableFrame(main_frame)
        scrollable_frame.grid(row=0, column=0, sticky="nsew")

        widget_data = {}
        radio_vars = {}

        for idx, item in enumerate(config_list):
            if not isinstance(item, dict):
                continue

            label = item.get("label", f"[Элемент без подписи №{idx}]")
            item_type = item.get("type", "unknown")

            if item_type in ("pane_title", "table_title"):
                ctk.CTkLabel(scrollable_frame, text=str(label), anchor="w",
                             font=('TkDefaultFont', 11, 'bold')).pack(fill="x", padx=15, pady=(8, 2))
                continue

            if item_type == "checkbox" and item.get("checkbox_element"):
                chk_data = item["checkbox_element"]
                bool_var = tk.BooleanVar(value=chk_data.get('checked', False))
                chk = ctk.CTkCheckBox(scrollable_frame, text=str(label), variable=bool_var,
                                       onvalue=True, offvalue=False)
                chk.pack(anchor="w", padx=15, pady=4)
                widget_data[label] = {
                    "type": "checkbox",
                    "widget": chk,
                    "var": bool_var,
                    "name": chk_data.get('name')
                }
                continue

            if item_type == "radio" and isinstance(item.get("radio_element"), dict):
                radio_data = item["radio_element"]
                group_name = radio_data.get("name") or f"radio_{idx}"
                radio_label = radio_data.get("label") if radio_data.get("label") is not None else ""
                opt_value = str(radio_data.get("value"))

                if group_name not in radio_vars:
                    radio_vars[group_name] = tk.StringVar(value=opt_value)
                if radio_data.get("selected"):
                    radio_vars[group_name].set(opt_value)

                rb = ctk.CTkRadioButton(scrollable_frame, text=str(radio_label),
                                        variable=radio_vars[group_name], value=opt_value)
                rb.pack(anchor="w", padx=15, pady=2)

                widget_data[idx] = {
                    "type": "radio",
                    "var": radio_vars[group_name],
                    "value": opt_value,
                }
                continue

            section_frame = ctk.CTkFrame(scrollable_frame)
            section_frame.pack(fill="x", pady=5, padx=10)

            ctk.CTkLabel(section_frame, text=str(label),
                          font=('TkDefaultFont', 9, 'bold')).pack(anchor='w')

            inner_frame = ctk.CTkFrame(section_frame, fg_color="transparent")
            inner_frame.pack(fill="x", padx=10, pady=5)

            if item_type == "text_field" and item.get("text_element"):
                text_data = item["text_element"]
                text_var = tk.StringVar(value=text_data.get('value', ''))

                ctk.CTkLabel(inner_frame, text="Значение:").grid(row=0, column=0, sticky="w")

                entry = ctk.CTkEntry(inner_frame, textvariable=text_var, width=350)
                entry.grid(row=0, column=1, sticky="ew", pady=5)

                widget_data[label] = {
                    "type": "text_field",
                    "widget": entry,
                    "var": text_var,
                    "name": text_data.get('name')
                }
                inner_frame.grid_columnconfigure(1, weight=1)

            elif item_type == "combo_box" and item.get("combo_box_element"):
                combo_options = item["combo_box_element"]
                selected_value = tk.StringVar()
                combo = ctk.CTkComboBox(
                    inner_frame,
                    variable=selected_value,
                    values=[opt.get('text') for opt in combo_options if 'text' in opt]
                )
                for opt in combo_options:
                    if opt.get('selected') is True and 'text' in opt:
                        selected_value.set(opt.get('text'))
                        break

                combo.grid(row=0, column=1, sticky="ew", pady=5)
                ctk.CTkLabel(inner_frame, text="Выбор:").grid(row=0, column=0, sticky="w")

                widget_data[label] = {
                    "type": "combo_box",
                    "widget": combo,
                    "options": combo_options,
                    "var": selected_value
                }
                inner_frame.grid_columnconfigure(1, weight=1)

            elif item_type == "table" and isinstance(item.get("table_element"), list):
                master_var = tk.BooleanVar()
                table_data = item["table_element"]
                table_widget = EditableTableWidget(inner_frame, table_data, master_var)

                widget_data[idx] = {
                    "type": "table",
                    "vars": table_widget.get_vars(),
                    "value_to_uid_map": table_widget.get_value_to_uid_map(),
                    "original_data": table_data,
                    "label": label,
                }

            else:
                ctk.CTkLabel(inner_frame,
                             text=json.dumps(item, ensure_ascii=False),
                             wraplength=700, justify="left").grid(row=0, column=0, sticky="w")

        def save_all_changes():
            for idx, item in enumerate(config_list):
                data = widget_data.get(idx)
                if data is None:
                    label = item.get("label")
                    if label:
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
                        option['selected'] = (option.get('text') == new_text)

                elif data["type"] == "checkbox":
                    new_state = data["var"].get()
                    if data["name"] and "checkbox_element" in item:
                        item["checkbox_element"]["checked"] = new_state

                elif data["type"] == "radio":
                    if "radio_element" in item:
                        item["radio_element"]["selected"] = (data["var"].get() == data["value"])

                elif data["type"] == "table":
                    value_to_uid_map = data["value_to_uid_map"]
                    for json_value, uid in value_to_uid_map.items():
                        if uid in data["vars"]:
                            new_state = data["vars"][uid].get()
                            for row in data["original_data"]:
                                chk_info = row.get("checkbox", {})
                                if chk_info.get("value") == json_value:
                                    row["checkbox"]["checked"] = new_state
                                    break

            try:
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE csoparams SET parameter = ? WHERE id = ?",
                    (json.dumps(config_list, ensure_ascii=False, separators=(',', ':')), report_id)
                )
                conn.commit()
                conn.close()
                messagebox.showinfo("Успех", "Все изменения сохранены!")
                edit_window.destroy()
            except Exception as e:
                messagebox.showerror("Ошибка БД", f"Не удалось сохранить данные: {e}")

        action_buttons = ctk.CTkFrame(main_frame, fg_color="transparent")
        action_buttons.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        save_btn = ctk.CTkButton(action_buttons, text="Сохранить все изменения",
                                 command=save_all_changes)
        save_btn.pack(side="left", padx=5)

        select_btn = ctk.CTkButton(action_buttons, text="Выбрать элемент",
                                   command=lambda: open_select_element_form(config_list))
        select_btn.pack(side="left", padx=5)

        edit_window.update_idletasks()
        activate_window(edit_window)

    except json.JSONDecodeError:
        messagebox.showerror("Ошибка JSON", "Данные из базы повреждены.")
    except sqlite3.Error as e:
        messagebox.showerror("Ошибка БД", f"Ошибка подключения: {e}")
    except Exception as e:
        messagebox.showerror("Критическая ошибка", f"Произошла ошибка: {e}")


def select_database():
    global db_path
    db_path = filedialog.askopenfilename(
        title="Выберите базу данных",
        filetypes=(("SQLite files", "*.db *.db3"), ("All Files", "*.*"))
    )
    if db_path:
        load_reports(db_path)
    else:
        messagebox.showwarning("Внимание", "Не выбран файл базы данных.")


def load_reports(db_path):
    result_text.pack_forget()

    connection = sqlite3.connect(db_path)
    cursor = connection.cursor()
    cursor.execute("SELECT id, note FROM csoparams")
    reports = cursor.fetchall()
    connection.close()

    clear_checkboxes()

    global var_states, report_checkboxes
    var_states = {}
    report_checkboxes = {}

    for idx, (id_, note_) in enumerate(reports):
        var = tk.BooleanVar()
        chkbtn = ctk.CTkCheckBox(
            report_scroll,
            text=f"{id_}: {note_}",
            variable=var,
            onvalue=True,
            offvalue=False
        )
        chkbtn.pack(anchor="w", pady=3, padx=5)
        var_states[id_] = var
        report_checkboxes[id_] = chkbtn

    apply_report_filter()


def apply_report_filter():
    query = search_var.get().strip().lower()
    for id_, chkbtn in report_checkboxes.items():
        text = chkbtn.cget("text").lower()
        should_show = (not query) or (query in text)
        if should_show and not chkbtn.winfo_ismapped():
            chkbtn.pack(anchor="w", pady=3, padx=5)
        elif not should_show and chkbtn.winfo_ismapped():
            chkbtn.pack_forget()


def clear_checkboxes():
    for widget in report_scroll.winfo_children():
        widget.destroy()
    global report_checkboxes
    report_checkboxes = {}


def delete_reports():
    selected_reports = [id_ for id_, var in var_states.items() if var.get()]
    if not selected_reports:
        messagebox.showwarning("Внимание", "Выберите хотя бы один отчет для удаления.")
        return

    confirmation = messagebox.askyesno("Подтверждение",
                                        f"Удалить {len(selected_reports)} отчетов навсегда?")
    if not confirmation:
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for report_id in selected_reports:
        cursor.execute("DELETE FROM csoparams WHERE id=?", (report_id,))
    conn.commit()
    conn.close()
    messagebox.showinfo("Готово", f"Удалено {len(selected_reports)} отчетов.")


def delete_element_form():
    form = ctk.CTkToplevel(root)
    form.title("Удалить элемент")
    form.geometry("450x300")

    ctk.CTkLabel(form, text="Укажите элемент для удаления:").pack(pady=5)
    element_entry = ctk.CTkTextbox(form, height=150, width=400)
    element_entry.pack(pady=5)

    submit_btn = ctk.CTkButton(
        form, text="Удалить",
        command=lambda: process_delete_element(element_entry.get("1.0", "end"))
    )
    submit_btn.pack(pady=10)
    activate_window(form)


def process_delete_element(user_input):
    new_element = user_input.strip()
    choose_reports_for_deleting(json.loads(new_element))


def process_new_element(user_input):
    try:
        new_element = json.loads(user_input)
    except json.JSONDecodeError:
        messagebox.showerror("Ошибка", "Неверный формат данных. Используйте корректный JSON.")
        return
    choose_reports_for_adding(new_element)


def add_new_element_form():
    global metka

    form = ctk.CTkToplevel(root)
    form.title("Добавить новый элемент")
    form.geometry("450x300")

    ctk.CTkLabel(form, text="Введите элемент (JSON):").pack(pady=5)
    element_entry = ctk.CTkTextbox(form, height=150, width=400)
    element_entry.pack(pady=5)

    frame_combo = ctk.CTkFrame(form, fg_color="transparent")
    frame_combo.pack(pady=5)

    ctk.CTkLabel(frame_combo, text="Вставить после:").pack(side="left")
    combo_type = ctk.CTkComboBox(
        frame_combo,
        values=["Период", "Район", "Поставщики", "Услуги"],
        width=180
    )
    combo_type.pack(side="left", padx=5)
    combo_type.set("Период")

    metka = combo_type.get()

    def update_metka(value):
        global metka
        metka = value
        messagebox.showinfo('Внимание', f'Элемент будет вставлен в раздел: {metka}')

    combo_type.configure(command=update_metka)

    submit_btn = ctk.CTkButton(
        form, text="Добавить",
        command=lambda: process_new_element(element_entry.get("1.0", "end"))
    )
    submit_btn.pack(pady=10)
    activate_window(form)


def choose_reports_for_adding(new_element):
    window = ctk.CTkToplevel(root)
    window.title("Выбор отчетов для добавления нового элемента")

    scroll = ctk.CTkScrollableFrame(window)
    scroll.pack(fill="both", expand=True, padx=10, pady=10)

    checkbuttons = []
    for id_ in sorted(var_states.keys()):
        var = tk.BooleanVar()
        chkbtn = create_select_checkbox(scroll, str(id_), var)
        chkbtn.pack(anchor="w", pady=3)
        checkbuttons.append((chkbtn, var))

    confirm_btn = ctk.CTkButton(
        scroll, text="Подтвердить",
        command=lambda: finalize_addition(new_element, checkbuttons, window)
    )
    confirm_btn.pack(pady=10)
    activate_window(window)


def finalize_addition(selected_element, checkbuttons, parent_top_level):
    selected_reports = [
        id_ for id_, var in
        zip([cb[0].cget("text") for cb in checkbuttons],
            [cb[1].get() for cb in checkbuttons])
        if var
    ]

    if not selected_reports:
        messagebox.showwarning("Внимание", "Выберите хотя бы один отчёт для добавления элемента.")
        return

    for report_id in selected_reports:
        add_element_to_report(report_id, selected_element, insert_before=metka)

    parent_top_level.destroy()


def compare_selected(var_states):
    selected_ids = [id_ for id_, var in var_states.items() if var.get()]
    if len(selected_ids) != 2:
        messagebox.showwarning("Внимание", "Выберите ровно два отчета для сравнения.")
        return

    missing_elements = compare_reports(selected_ids, db_path)
    if missing_elements:
        open_add_or_remove_form(missing_elements)


def open_add_or_remove_form(missing_elements):
    top_level = ctk.CTkToplevel(root)
    top_level.title("Добавить или удалить элемент")
    top_level.geometry("1500x500")

    upper_container = ctk.CTkFrame(top_level, fg_color="transparent")
    upper_container.pack(fill="both", expand=True)

    lower_container = ctk.CTkFrame(top_level, fg_color="transparent")
    lower_container.pack(fill="x", side="bottom")

    scroll = ctk.CTkScrollableFrame(upper_container)
    scroll.pack(fill="both", expand=True)

    choice_var = tk.IntVar()

    for idx, missing in enumerate(missing_elements):
        element_text = json.dumps(missing, ensure_ascii=False, separators=(',', ':'))

        ctk.CTkLabel(scroll, text=element_text, wraplength=1400, justify="left").pack(
            anchor="w", pady=5, padx=10
        )

        rb = ctk.CTkRadioButton(
            scroll, text=f"Выбрать элемент №{idx+1}",
            variable=choice_var, value=idx
        )
        rb.pack(anchor="w", pady=3, padx=20)

    add_btn = ctk.CTkButton(
        lower_container, text="Добавить",
        command=lambda: handle_add_action(missing_elements, choice_var.get(), top_level)
    )
    add_btn.pack(side="left", padx=10, pady=10)

    delete_btn = ctk.CTkButton(
        lower_container, text="Удалить",
        command=lambda: handle_delete_action(missing_elements, choice_var.get(), top_level)
    )
    delete_btn.pack(side="left", padx=10, pady=10)
    activate_window(top_level)


def handle_add_action(missing_elements, index, parent_top_level):
    selected_element = missing_elements[index]
    parent_top_level.destroy()
    choose_reports_for_adding(selected_element)


def handle_delete_action(missing_elements, index, parent_top_level):
    selected_element = missing_elements[index]
    parent_top_level.destroy()
    choose_reports_for_deleting(selected_element)


def choose_reports_for_deleting(selected_element):
    window = ctk.CTkToplevel(root)
    window.title("Выбор отчетов для удаления")
    window.geometry("400x300")

    scroll = ctk.CTkScrollableFrame(window)
    scroll.pack(fill="both", expand=True, padx=10, pady=10)

    checkbuttons = []
    for id_ in sorted(var_states.keys()):
        var = tk.BooleanVar()
        chkbtn = create_select_checkbox(scroll, str(id_), var)
        chkbtn.pack(anchor="w", pady=3)
        checkbuttons.append((chkbtn, var))

    confirm_btn = ctk.CTkButton(
        scroll, text="Подтвердить",
        command=lambda: finalize_deletion(selected_element, checkbuttons, window)
    )
    confirm_btn.pack(pady=10)
    activate_window(window)


def finalize_deletion(selected_element, checkbuttons, parent_top_level):
    selected_reports = [
        id_ for id_, var in
        zip([cb[0].cget("text") for cb in checkbuttons],
            [cb[1].get() for cb in checkbuttons])
        if var
    ]

    if not selected_reports:
        messagebox.showwarning("Внимание", "Выберите хотя бы один отчёт для удаления элемента.")
        return

    for report_id in selected_reports:
        remove_element_from_report(report_id, selected_element)

    parent_top_level.destroy()


TABLE_CATEGORIES = {
    "Поставщики": {
        "names": {"post", "postav", "postav_list"},
        "prefixes": ("table_post", "table_postav"),
    },
    "Услуги": {
        "names": {"usl", "serv", "serv_list", "service"},
        "prefixes": ("table_usl", "table_serv"),
    },
}


def row_matches_category(row, category):
    if not isinstance(row, dict):
        return False
    names = TABLE_CATEGORIES[category]["names"]
    prefixes = TABLE_CATEGORIES[category]["prefixes"]
    chk = row.get("checkbox")
    if isinstance(chk, dict) and chk.get("name") in names:
        return True
    html_id = str(row.get("htmlId", ""))
    if any(html_id.lower().startswith(p) for p in prefixes):
        return True
    return False


def add_element_to_report(report_id, element, insert_before=None):
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

        if metka in TABLE_CATEGORIES:
            target_table = None
            for item in config_list:
                if not isinstance(item, dict) or item.get('type') != 'table':
                    continue
                rows = item.get('table_element')
                if not isinstance(rows, list):
                    continue
                if any(row_matches_category(row, metka) for row in rows):
                    target_table = item
                    break

            if target_table is not None:
                table_data = target_table['table_element']
                insert_position = len(table_data)
                new_name = str(element.get('col1', '')).upper()

                for idx, row in enumerate(table_data[1:], start=1):
                    current_name = str(row.get('col1', '')).upper()
                    if new_name < current_name:
                        insert_position = idx
                        break

                table_data.insert(insert_position, element)
                element_added = True

        elif metka in ["Период", "Район"]:
            for i in range(len(config_list)):
                current_item = config_list[i]
                is_target_field = (
                    current_item.get('type') == 'text_field' and
                    current_item.get('label') == metka
                )
                if is_target_field:
                    config_list.insert(i + 1, element)
                    element_added = True
                    break

        if not element_added and metka not in ["Период", "Район"] + list(TABLE_CATEGORIES):
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

        def recursive_remove(obj):
            nonlocal element_removed

            if isinstance(obj, list):
                for i, item in enumerate(obj[:]):
                    if item == element_to_find:
                        obj.remove(item)
                        element_removed = True
                    else:
                        recursive_remove(item)

            elif isinstance(obj, dict):
                if 'table_element' in obj and isinstance(obj['table_element'], list):
                    recursive_remove(obj['table_element'])
                else:
                    for key in obj:
                        recursive_remove(obj[key])

        recursive_remove(config_list)

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


def show_result_gui(report_id, element):
    top_level = ctk.CTkToplevel(root)
    top_level.title("Результат добавления / удаления")

    info_label = ctk.CTkLabel(
        top_level,
        text=f"Операция успешно проведена в отчёте с ID {report_id}.\n\n"
             f"Детали элемента:\n"
             f"{json.dumps(element, ensure_ascii=False, separators=(',', ':'))}"
    )
    info_label.pack(pady=10)

    close_btn = ctk.CTkButton(top_level, text="Закрыть", command=top_level.destroy)
    close_btn.pack(pady=10)
    activate_window(top_level)


# === ГЛАВНОЕ ОКНО ===
root = ctk.CTk()
root.title("Работа с базой Smapp.3db v1.3")

app_dir = pathlib.Path(__file__).resolve().parent
icon_path = os.path.join(app_dir, 'osa.ico')
try:
    root.iconbitmap(icon_path)
except Exception:
    pass

root.geometry("1000x700")

content_frame = ctk.CTkFrame(root, fg_color="transparent")
content_frame.pack(fill="both", expand=True, padx=10, pady=10)
content_frame.grid_columnconfigure(1, weight=1)
content_frame.grid_rowconfigure(0, weight=1)

# Левая панель — кнопки
left_panel = ctk.CTkFrame(content_frame, width=220)
left_panel.grid(row=0, column=0, sticky="ns", padx=(0, 5))
left_panel.pack_propagate(False)

ctk.CTkButton(left_panel, text="Выбрать базу данных", command=select_database).pack(
    pady=(15, 5), padx=10, fill="x"
)

ctk.CTkFrame(left_panel, height=2, fg_color="gray50").pack(fill="x", padx=10, pady=10)

ctk.CTkButton(left_panel, text="Сравнить",
              command=lambda: compare_selected(var_states)).pack(pady=3, padx=10, fill="x")

ctk.CTkButton(left_panel, text="Редактировать отчёт",
              command=lambda: update_selected(var_states)).pack(pady=3, padx=10, fill="x")

ctk.CTkButton(left_panel, text="Добавить элемент JSON",
              command=add_new_element_form).pack(pady=3, padx=10, fill="x")

ctk.CTkButton(left_panel, text="Удалить элемент JSON",
              command=delete_element_form).pack(pady=3, padx=10, fill="x")

ctk.CTkButton(left_panel, text="Удалить отчёт",
              command=delete_reports,
              fg_color="#c0392b", hover_color="#e74c3c").pack(pady=3, padx=10, fill="x")

# Правая панель — список отчётов + результат
right_panel = ctk.CTkFrame(content_frame)
right_panel.grid(row=0, column=1, sticky="nsew", padx=(5, 0))

filter_frame = ctk.CTkFrame(right_panel, fg_color="transparent")
filter_frame.pack(fill="x", padx=5, pady=(5, 0))

ctk.CTkLabel(filter_frame, text="Фильтр:").pack(side="left", padx=(0, 5))
search_var = tk.StringVar()
search_var.trace_add('write', lambda *args: apply_report_filter())
search_entry = ctk.CTkEntry(filter_frame, textvariable=search_var, placeholder_text="ID или текст...")
search_entry.pack(side="left", fill="x", expand=True)

report_scroll = ctk.CTkScrollableFrame(right_panel)
report_scroll.pack(fill="both", expand=True, padx=5, pady=5)

result_text = ctk.CTkTextbox(right_panel, height=200)
result_text.pack_forget()

# Глобальные переменные
db_path = None
checkbuttons = []
var_states = {}
report_checkboxes = {}
metka = ""

root.mainloop()
