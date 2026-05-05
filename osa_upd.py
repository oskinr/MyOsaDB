import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import pathlib

class DBTransferApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Перенос данных между SQLite базами")
        self.root.geometry("800x500")
        app_dir = pathlib.Path(__file__).resolve().parent
        icon_path = os.path.join(app_dir, 'osa.ico')
        try:
            root.iconbitmap(icon_path)
        except Exception as e:
            pass

        self.source_path = tk.StringVar()
        self.target_path = tk.StringVar()
        self.selected_table = tk.StringVar()
        self.columns = []

        self.create_widgets()

    def create_widgets(self):
        # --- Пути к базам ---
        frame_paths = ttk.LabelFrame(self.root, text="Пути к базам данных", padding="10")
        frame_paths.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_paths, text="База-источник:").grid(row=0, column=0, sticky="e", pady=2)
        ttk.Entry(frame_paths, textvariable=self.source_path, width=60).grid(row=0, column=1, sticky="ew", pady=2)
        ttk.Button(frame_paths, text="...", command=lambda: self.select_file(self.source_path)).grid(row=0, column=2, pady=2)

        ttk.Label(frame_paths, text="База-приемник:").grid(row=1, column=0, sticky="e", pady=2)
        ttk.Entry(frame_paths, textvariable=self.target_path, width=60).grid(row=1, column=1, sticky="ew", pady=2)
        ttk.Button(frame_paths, text="...", command=lambda: self.select_file(self.target_path)).grid(row=1, column=2, pady=2)

        # --- Выбор таблицы ---
        frame_table = ttk.Frame(self.root, padding="10")
        frame_table.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame_table, text="Таблица:").pack(side="left")
        self.combo_tables = ttk.Combobox(frame_table, textvariable=self.selected_table, state="readonly")
        self.combo_tables.pack(side="left", padx=5)
        ttk.Button(frame_table, text="Обновить список таблиц", command=self.load_tables).pack(side="left")

        # --- Кнопка загрузки данных ---
        frame_controls = ttk.Frame(self.root, padding="10")
        frame_controls.pack(fill="x", padx=10, pady=5)

        ttk.Button(frame_controls, text="Загрузить данные таблицы", command=self.load_data).pack(side="left", padx=5)
        
        self.progress = ttk.Progressbar(frame_controls, orient="horizontal", mode="determinate")
        self.progress.pack(side="left", fill="x", expand=True, padx=5)

        # --- Treeview для данных ---
        frame_data = ttk.Frame(self.root)
        frame_data.pack(fill="both", expand=True, padx=10, pady=5)

        self.tree = ttk.Treeview(frame_data)
        self.tree.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame_data, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

        # --- Кнопка переноса ---
        frame_actions = ttk.Frame(self.root)
        frame_actions.pack(fill="x", padx=10, pady=5)

        ttk.Button(frame_actions, text="Перенести выбранные", command=self.transfer_selected).pack(side="left")

    def select_file(self, string_var):
        filename = filedialog.askopenfilename(filetypes=[("SQLite DB", "*.db3;*.db;*.sqlite")])
        if filename:
            string_var.set(filename)
            # При выборе файла обновляем список таблиц
            self.load_tables()

    def load_tables(self):
        path = self.source_path.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Ошибка", "Путь к базе-источнику не указан или файл не найден.")
            return

        try:
            with sqlite3.connect(path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = [row[0] for row in cur.fetchall()]
                self.combo_tables['values'] = tables
                if tables:
                    self.selected_table.set(tables[0])
                else:
                    self.combo_tables.set('')
                    self.tree.delete(*self.tree.get_children())
                    messagebox.showinfo("Информация", "В базе нет таблиц.")
            self.columns = []
            self.tree.delete(*self.tree.get_children())
            self.tree['columns'] = ()
            self.tree.heading('#0', text='Выберите таблицу')
            self.tree.insert("", "end", text="Выберите таблицу из списка и нажмите 'Загрузить данные таблицы'")

        except sqlite3.Error as e:
            messagebox.showerror("Ошибка БД", f"Не удалось получить список таблиц: {e}")

    def load_data(self):
        table_name = self.selected_table.get()
        if not table_name:
            messagebox.showwarning("Внимание", "Выберите таблицу.")
            return

        path = self.source_path.get()
        if not path or not os.path.exists(path):
            messagebox.showerror("Ошибка", "Путь к базе-источнику не указан или файл не найден.")
            return

        self.tree.delete(*self.tree.get_children())
        
        try:
            with sqlite3.connect(path) as conn:
                cur = conn.cursor()
                cur.execute(f"PRAGMA table_info({table_name})")
                columns_info = cur.fetchall()
                columns = [col[1] for col in columns_info]
                self.columns = columns

                # Настраиваем колонки Treeview динамически
                self.tree.config(columns=columns, show="headings")
                for col in columns:
                    self.tree.heading(col, text=col.capitalize())
                    self.tree.column(col, minwidth=0, width=170, stretch=False)
                
                # Загружаем все строки из таблицы
                cur.execute(f"SELECT * FROM {table_name}")
                rows = cur.fetchall()
                
                if not rows:
                    messagebox.showinfo("Информация", "Таблица пуста.")
                    return

                for row in rows:
                    values = dict(zip(columns, row))
                    # Используем id как iid для удобства переноса (если есть колонка id)
                    iid = values.get('id', '')
                    self.tree.insert("", "end", iid=iid, values=tuple(values.values()))

            messagebox.showinfo("Успех", f"Загружено {len(rows)} записей.")
            
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка БД", f"Не удалось прочитать данные: {e}")

    def transfer_selected(self):
        selected_items = self.tree.selection()
        
        if not selected_items:
            messagebox.showwarning("Внимание", "Выберите строки для переноса.")
            return

        source_path = self.source_path.get()
        target_path = self.target_path.get()
        
        if not source_path or not target_path:
            messagebox.showerror("Ошибка", "Укажите пути к обеим базам данных.")
            return

        table_name = self.selected_table.get()
        
        self.progress["value"] = 0
        self.root.update_idletasks()
        
        try:
            # Читаем данные из источника по выбранным id
            with sqlite3.connect(source_path) as src_conn:
                src_cur = src_conn.cursor()
                src_cur.execute(f"SELECT * FROM {table_name} WHERE id IN ({','.join('?'*len(selected_items))})", tuple(selected_items))
                rows_to_transfer = src_cur.fetchall()
            
            total = len(rows_to_transfer)
            if total == 0:
                messagebox.showinfo("Информация", "Нет данных для выбранных ID.")
                return

            # Получаем имена колонок для вставки
            with sqlite3.connect(target_path) as tgt_conn:
                tgt_cur = tgt_conn.cursor()
                tgt_cur.execute(f"PRAGMA table_info({table_name})")
                columns_info = tgt_cur.fetchall()
                columns = [col[1] for col in columns_info]
                
                # Индекс id в списке колонок (если есть)
                id_index = None
                for i, col in enumerate(columns):
                    if col == 'id':
                        id_index = i
                        break

                # Получаем максимальный id в целевой базе (если есть id)
                next_new_id = 1
                if id_index is not None:
                    tgt_cur.execute(f"SELECT MAX(id) FROM {table_name}")
                    max_id_result = tgt_cur.fetchone()
                    next_new_id = (max_id_result[0] or 0) + 1

                inserted_count = 0

                for row in rows_to_transfer:
                    current_id = row[id_index] if id_index is not None else None
                    
                    # Проверяем занятость id (если есть id)
                    is_id_taken = False
                    if id_index is not None:
                        tgt_cur.execute(f"SELECT COUNT(*) FROM {table_name} WHERE id = ?", (current_id,))
                        is_id_taken = tgt_cur.fetchone()[0] > 0

                    if is_id_taken:
                        new_id = next_new_id
                        next_new_id += 1
                        new_row = list(row)
                        new_row[id_index] = new_id
                        new_row = tuple(new_row)
                    else:
                        new_row = row

                    placeholders = ', '.join(['?'] * len(columns))
                    insert_query = f"INSERT INTO {table_name} VALUES ({placeholders})"
                    
                    tgt_cur.execute(insert_query, new_row)
                    inserted_count += 1
                    
                    self.progress["value"] = (inserted_count / total) * 100
                    self.root.update_idletasks()
                
                tgt_conn.commit()
            
            messagebox.showinfo("Успех", f"Перенесено {inserted_count} строк.")
            
        except sqlite3.Error as e:
            messagebox.showerror("Ошибка БД", f"Произошла ошибка при переносе: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = DBTransferApp(root)
    root.mainloop()