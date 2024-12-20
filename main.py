import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import os
import shutil
import time
import webbrowser
import pyperclip

import useful_info
import news

def create_connection():
    conn = sqlite3.connect('app_database.db')
    return conn

def create_tables():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY,
            sender_id INTEGER NOT NULL,
            receiver_id INTEGER NOT NULL,
            content TEXT,
            file_path TEXT,
            image_path TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            receiver_type TEXT DEFAULT 'user',
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS group_members (
            group_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            FOREIGN KEY (group_id) REFERENCES groups(id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            CONSTRAINT pk_group_members PRIMARY KEY (group_id, user_id)
        );
    ''')

    conn.commit()
    conn.close()

def create_user(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?);', (username, password))
        conn.commit()
        messagebox.showinfo("Успех", "Пользователь успешно зарегистрирован.")
        user_id = cursor.lastrowid
        set_current_user(user_id, username)
        update_ui_after_login()
    except sqlite3.IntegrityError:
        messagebox.showerror("Ошибка", "Имя пользователя уже существует.")
    finally:
        conn.close()

def authenticate_user(username, password):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?;', (username, password))
    user = cursor.fetchone()
    conn.close()
    return user[0] if user else None

def login():
    username = simpledialog.askstring("Вход", "Введите имя пользователя:")
    if username:
        password = simpledialog.askstring("Вход", "Введите пароль:", show="*")
        if password:
            user_id = authenticate_user(username, password)
            if user_id:
                set_current_user(user_id, username)
                update_ui_after_login()
            else:
                messagebox.showerror("Ошибка", "Неверное имя пользователя или пароль.")

def register():
    register_window = tk.Toplevel(root)
    register_window.title("Регистрация пользователя")
    register_window.geometry("300x200")

    tk.Label(register_window, text="Имя пользователя:").pack(pady=5)
    username_entry = tk.Entry(register_window, width=30)
    username_entry.pack(pady=5)

    tk.Label(register_window, text="Пароль:").pack(pady=5)
    password_entry = tk.Entry(register_window, width=30, show="*")
    password_entry.pack(pady=5)

    def submit_registration():
        username = username_entry.get().strip()
        password = password_entry.get().strip()

        if len(username) == 0 or len(password) == 0:
            messagebox.showwarning("Ошибка", "Логин или пароль нельзя оставить пустыми.")
            return  

        try:
            print(f"Регистрируем: {username}, {password}")
            create_user(username, password)
            register_window.destroy()
        except sqlite3.IntegrityError:
            messagebox.showerror("Ошибка", "Имя пользователя уже используется.")
        except Exception as e:
            print(f"Ошибка при создании пользователя: {e}")
            messagebox.showinfo("Неожиданная ошибка", str(e))

    submit_button = tk.Button(register_window, text="Зарегистрироваться", command=submit_registration)
    submit_button.pack(pady=10)

def set_current_user(user_id, username):
    global current_user_id
    global current_username
    current_user_id = user_id
    current_username = username
    with open('current_user.txt', 'w') as f:
        f.write(f"{user_id},{username}")
    username_label.config(text=f"Пользователь: {current_username} (ID: {current_user_id})")

def get_current_user():
    if os.path.exists('current_user.txt'):
        with open('current_user.txt', 'r') as f:
            try:
                user_id, username = f.read().split(',')
                return int(user_id), username
            except ValueError:
                return None, None
    return None, None

def logout():
    global current_user_id
    global current_username
    current_user_id = None
    current_username = None
    if os.path.exists('current_user.txt'):
        os.remove('current_user.txt')
    update_ui_after_logout()

def update_user_details(user_id, new_username=None, new_password=None):
    conn = create_connection()
    cursor = conn.cursor()

    if new_username and new_password:
        hashed_password = new_password
        cursor.execute('UPDATE users SET username = ?, password = ? WHERE id = ?;', (new_username, hashed_password, user_id))
    elif new_username:
        cursor.execute('UPDATE users SET username = ? WHERE id = ?;', (new_username, user_id))
    elif new_password:
        hashed_password = new_password
        cursor.execute('UPDATE users SET password = ? WHERE id = ?;', (hashed_password, user_id))

    conn.commit()
    conn.close()

def start_video_call(receiver_id):
    room_name = f"ChatApp_Room_{current_user_id}_{receiver_id}"  
    jitsi_url = f"https://meet.jit.si/{room_name}"  
    webbrowser.open(jitsi_url)  
    messagebox.showinfo(
        "Видеозвонок",
        f"Видеозвонок начнется в браузере в комнате: {room_name}"
    )

def create_group(group_name, member_ids):
    conn = create_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('INSERT INTO groups (name) VALUES (?);', (group_name,))
        group_id = cursor.lastrowid

        for user_id in member_ids:
            cursor.execute('INSERT INTO group_members (group_id, user_id) VALUES (?, ?);', (group_id, user_id))

        conn.commit()
        return group_id
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка при создании группы: {e}")
    finally:
        conn.close()

def add_user_to_group(group_id, user_id):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO group_members (group_id, user_id) VALUES (?, ?);', (group_id, user_id))
        conn.commit()
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка: {e}")
    finally:
        conn.close()

def get_group_members(group_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT users.id, users.username 
        FROM group_members
        JOIN users ON group_members.user_id = users.id
        WHERE group_members.group_id = ?;
    ''', (group_id,))
    members = cursor.fetchall()
    conn.close()
    return members

def load_group_messages(group_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT sender_id, content, timestamp, file_path, image_path 
        FROM messages 
        WHERE receiver_id = ? AND receiver_type = 'group'
        ORDER BY timestamp;
    ''', (group_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages

def send_group_message(sender_id, group_id, content, file_path=None, image_path=None):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
        INSERT INTO messages (sender_id, receiver_id, content, file_path, image_path, receiver_type)
        VALUES (?, ?, ?, ?, ?, ?);
            ''', (sender_id, group_id, content, file_path, image_path, 'group'))
        conn.commit()
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка отправки сообщения: {e}")
    finally:
        conn.close()

def show_group_chats():
    clear_content_frame()
    tk.Label(content_frame, text="Групповые чаты", font=("Arial", 16)).pack(pady=10)

    groups = get_user_groups(current_user_id)

    if groups:
        tk.Label(content_frame, text="Ваши группы:", font=("Arial", 14)).pack(pady=5)

        chat_list_frame = tk.Frame(content_frame)
        chat_list_frame.pack(pady=5, fill=tk.BOTH, expand=True)

        chat_list_frame.columnconfigure(0, weight=1)
        chat_list_frame.columnconfigure(1, weight=1)

        for row, (group_id, group_name) in enumerate(groups):
            row_frame = tk.Frame(chat_list_frame)
            row_frame.grid(row=row, column=0, columnspan=2, pady=5)

            row_frame.columnconfigure(0, weight=1)
            row_frame.columnconfigure(1, weight=1)

            group_button = tk.Button(row_frame, text=group_name, command=lambda group_id=group_id: open_group_chat_window(group_id))
            group_button.grid(row=0, column=0, padx=10, sticky="e")

            delete_button = tk.Button(row_frame, text="Удалить", bg="red",
                                      command=lambda group_id=group_id: delete_group_chat(group_id))
            delete_button.grid(row=0, column=1, padx=10, sticky="w")

        create_group_button = tk.Button(content_frame, text="Создать новую группу", command=create_new_group_window)
        create_group_button.pack(pady=10)
    else:
        tk.Label(content_frame, text="У вас пока нет групповых чатов.", font=("Arial", 14)).pack(pady=10)

        create_group_button = tk.Button(content_frame, text="Создать новую группу", command=create_new_group_window)
        create_group_button.pack(pady=10)

def get_user_groups(user_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT groups.id, groups.name 
        FROM group_members
        JOIN groups ON group_members.group_id = groups.id
        WHERE group_members.user_id = ?;
    ''', (user_id,))
    groups = cursor.fetchall()
    conn.close()
    return groups

def create_new_group_window():
    new_group_window = tk.Toplevel(root)
    new_group_window.title("Создать новую группу")
    new_group_window.geometry("300x200")

    tk.Label(new_group_window, text="Название группы:").pack(pady=5)
    group_name_entry = tk.Entry(new_group_window, width=30)
    group_name_entry.pack(pady=5)

    tk.Label(new_group_window, text="Введите ID участников (через пробел):").pack(pady=5)
    participants_entry = tk.Entry(new_group_window, width=30)
    participants_entry.pack(pady=5)

    def submit_new_group():
        group_name = group_name_entry.get().strip()
        participants = participants_entry.get().strip().split()

        if group_name and participants:
            try:
                participant_ids = [int(p) for p in participants]
                participant_ids.append(current_user_id)   
                create_group(group_name, participant_ids)
                messagebox.showinfo("Успех", f"Группа '{group_name}' успешно создана!")
                new_group_window.destroy()
                show_group_chats()
            except ValueError:
                messagebox.showerror("Ошибка", "Пожалуйста, введите корректные ID участников.")
        else:
            messagebox.showerror("Ошибка", "Название группы или участники не указаны.")

    submit_button = tk.Button(new_group_window, text="Создать группу", command=submit_new_group)
    submit_button.pack(pady=10)

def open_group_chat_window(group_id):
    group_chat_window = tk.Toplevel(root)
    group_chat_window.title("Групповой чат")
    group_chat_window.geometry("500x600")

    members = get_group_members(group_id)
    tk.Label(group_chat_window, text="Участники группы:", font=("Arial", 14)).pack(pady=10)
    for member_id, member_name in members:
        tk.Label(group_chat_window, text=f"- {member_name} (ID: {member_id})", font=("Arial", 12)).pack(anchor="w")

    tk.Label(group_chat_window, text="Сообщения:", font=("Arial", 14)).pack(pady=10)

    messages_frame = tk.Frame(group_chat_window)
    messages_frame.pack(fill=tk.BOTH, expand=True)

    def refresh_messages():
        for widget in messages_frame.winfo_children():
            widget.destroy()

        messages = load_group_messages(group_id)
        for message in messages:
            sender = "Вы" if message[0] == current_user_id else f"Пользователь {message[0]}"
            message_text = f"{message[2]} - {sender}: {message[1]}"
            
            message_container = tk.Frame(messages_frame)
            message_container.pack(anchor="w", pady=5)

            tk.Label(message_container, text=message_text).pack(anchor="w")

            if message[3]: 
                file_name = os.path.basename(message[3])

                def download_file(path=message[3]):
                    if os.path.exists(path):
                        save_path = filedialog.asksaveasfilename(initialfile=file_name)
                        if save_path:
                            shutil.copy(path, save_path)
                            messagebox.showinfo("Успех", f"Файл сохранен: {save_path}")
                    else:
                        messagebox.showerror("Ошибка", "Файл не найден.")

                tk.Button(messages_frame, text=f"Скачать файл: {file_name}", command=download_file).pack(anchor="w")

            if message[1]: 
                copy_button = tk.Button(message_container, text="Копировать", command=lambda msg=message[1]: copy_to_clipboard(msg))
                copy_button.pack(anchor="w", pady=2)

    def submit_group_message():
        content = message_entry.get()
        if not (content.strip() or selected_file_path):  
            return  

        file_destination = None
        image_destination = None

        if selected_file_path:
            if not os.path.exists('files'):
                os.makedirs('files') 
            unique_filename = f"{current_user_id}_{int(time.time())}_{os.path.basename(selected_file_path)}"
            file_destination = os.path.join('files', unique_filename)
            shutil.copy(selected_file_path, file_destination)

        send_group_message(current_user_id, group_id, content, file_path=file_destination, image_path=image_destination)

        message_entry.delete(0, tk.END)
        clear_attachments()
        attachments_label.config(text="Нет прикреплений")
        refresh_messages()

    message_entry = tk.Entry(group_chat_window, width=50)
    message_entry.pack(pady=5)

    message_entry.bind("<Return>", lambda event: submit_group_message())

    attachments_label = tk.Label(group_chat_window, text="Нет прикреплений")
    attachments_label.pack(pady=5)

    button_frame = tk.Frame(group_chat_window)
    button_frame.pack(pady=10)

    attach_file_button = tk.Button(button_frame, text="Прикрепить файл", command=lambda: attach_file(attachments_label))
    attach_file_button.grid(row=0, column=0, padx=5)

    send_message_button = tk.Button(button_frame, text="Отправить", command=submit_group_message)
    send_message_button.grid(row=1, column=0, padx=5)

    refresh_messages()
    group_chat_window.after(1000, refresh_messages)

def delete_group_chat(group_id):
    if messagebox.askyesno("Подтверждение", f"Вы действительно хотите удалить группу (ID: {group_id}) из вашего списка?"):
        conn = create_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                DELETE FROM group_members 
                WHERE group_id = ? AND user_id = ?;
            ''', (group_id, current_user_id))
            conn.commit()
            messagebox.showinfo("Успех", "Вы были удалены из группы.")
            show_group_chats()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка: {e}")
        finally:
            conn.close()

def find_user(identifier):
    conn = create_connection()
    cursor = conn.cursor()
    if identifier.isdigit():
        cursor.execute('SELECT id, username FROM users WHERE id = ?;', (int(identifier),))
    else:
        cursor.execute('SELECT id, username FROM users WHERE username = ?;', (identifier,))
    user = cursor.fetchone()
    conn.close()
    return user

def create_message(sender_id, receiver_id, content, file_path=None, image_path=None):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, content, file_path, image_path)
            VALUES (?, ?, ?, ?, ?);
        ''', (sender_id, receiver_id, content, file_path, image_path))
        conn.commit()
    except Exception as e:
        messagebox.showerror("Ошибка", f"Ошибка отправки сообщения: {e}")
    finally:
        conn.close()

def load_messages(user_id, chat_with_id=None):
    conn = create_connection()
    cursor = conn.cursor()
    if chat_with_id:
        cursor.execute('''
            SELECT sender_id, content, timestamp, file_path, image_path 
            FROM messages 
            WHERE ((sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?))
            AND receiver_type = 'user'
            AND sender_id != receiver_id  -- Исключить сообщения самому себе
            ORDER BY timestamp;
        ''', (user_id, chat_with_id, chat_with_id, user_id))
    else:
        cursor.execute('''
            SELECT sender_id, content, timestamp, file_path, image_path 
            FROM messages 
            WHERE receiver_id = ? AND receiver_type = 'user'
            AND sender_id != receiver_id  -- Исключить сообщения самому себе
            ORDER BY timestamp;
        ''', (user_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages

def send_message():
    receiver_input = simpledialog.askstring("Отправка сообщения", "Введите ID или имя получателя:")
    if receiver_input:
        receiver = find_user(receiver_input)
        if receiver:
            receiver_id = receiver[0]
            content = message_entry.get()
            message_entry.bind("<Return>", lambda event: send_message())
            if receiver_id and (content or selected_file_path):
                file_destination = None
                image_destination = None

                if selected_file_path:
                    if not os.path.exists('files'):
                        os.makedirs('files')
                    unique_filename = f"{current_user_id}_{int(time.time())}_{os.path.basename(selected_file_path)}"
                    file_destination = os.path.join('files', unique_filename)
                    shutil.copy(selected_file_path, file_destination)

                create_message(current_user_id, receiver_id, content, file_destination, image_destination)
                message_entry.delete(0, tk.END)
                clear_attachments()
                attachments_label.config(text="Нет прикреплений")
                refresh_messages()
            else:
                pass
        else:
            messagebox.showerror("Ошибка", "Пользователь не найден.")

def refresh_messages():
    messages = load_messages(current_user_id)
    messages_list.delete(0, tk.END)
    for message in messages:
        display_message(messages_list, message)

def update_ui_after_login():
    login_button.pack_forget()
    register_button.pack_forget()
    top_frame.pack(side=tk.TOP, fill=tk.X)
    content_frame.pack(fill=tk.BOTH, expand=True)
    news.show_news_section(content_frame)

def update_ui_after_logout():
    top_frame.pack_forget()
    content_frame.pack_forget()
    username_label.config(text="")
    login_button.pack(pady=5)
    register_button.pack(pady=5)

def open_chat_window(receiver_id):
    global global_receiver_id
    global_receiver_id = receiver_id
    chat_window = tk.Toplevel(root)
    chat_window.title(f"Чат с пользователем {receiver_id}")
    chat_window.geometry("500x600")

    chat_messages_frame = tk.Frame(chat_window)
    chat_messages_frame.pack(pady=10, fill=tk.BOTH, expand=True)

    chat_canvas = tk.Canvas(chat_messages_frame)
    chat_scrollbar = tk.Scrollbar(chat_messages_frame, orient="vertical", command=chat_canvas.yview)
    chat_scrollable_frame = tk.Frame(chat_canvas)

    chat_scrollable_frame.bind(
        "<Configure>",
        lambda e: chat_canvas.configure(
            scrollregion=chat_canvas.bbox("all")
        )
    )
    chat_canvas.create_window((0, 0), window=chat_scrollable_frame, anchor='nw')
    chat_canvas.configure(yscrollcommand=chat_scrollbar.set)
    
    chat_canvas.pack(side="left", fill="both", expand=True)
    chat_scrollbar.pack(side="right", fill="y")

    chat_message_entry = tk.Entry(chat_window, width=50)
    chat_message_entry.pack(pady=10)
    chat_message_entry.bind("<Return>", lambda event: send_chat_message())

    chat_attachments_label = tk.Label(chat_window, text="Нет прикреплений")
    chat_attachments_label.pack(pady=5)
    
    chat_attach_file_button = tk.Button(chat_window, text="Прикрепить файл", command=lambda: attach_chat_file(chat_attachments_label))
    chat_attach_file_button.pack(pady=2)


    def send_chat_message():
        content = chat_message_entry.get()
        if content or selected_chat_file_path:
            file_destination = None
            image_destination = None

            if selected_chat_file_path:
                if not os.path.exists('files'):
                    os.makedirs('files')
                unique_filename = f"{current_user_id}_{int(time.time())}_{os.path.basename(selected_chat_file_path)}"
                file_destination = os.path.join('files', unique_filename)
                shutil.copy(selected_chat_file_path, file_destination)

            create_message(current_user_id, receiver_id, content, file_destination, image_destination)
            chat_message_entry.delete(0, tk.END)
            clear_chat_attachments()
            chat_attachments_label.config(text="Нет прикреплений")
            refresh_chat_messages(chat_scrollable_frame, receiver_id)
        else:
            pass

    chat_send_button = tk.Button(chat_window, text="Отправить", command=send_chat_message)
    chat_send_button.pack(pady=5)

    def refresh_chat():
        refresh_chat_messages(chat_scrollable_frame, receiver_id)
        chat_window.after(1000, refresh_chat)

    refresh_chat()

def refresh_chat_messages(container, receiver_id):
    for widget in container.winfo_children():
        widget.destroy()

    messages = load_messages(current_user_id, receiver_id)

    for message in messages:
        message_frame = tk.Frame(container)
        message_frame.pack(pady=5, anchor='w' if message[0] == current_user_id else 'e')

        sender = "Вы" if message[0] == current_user_id else f"Пользователь {message[0]}"
        timestamp_label = tk.Label(message_frame, text=f"{message[2]} - {sender}")
        timestamp_label.pack(anchor='w')

        if message[1]:
            content_label = tk.Label(message_frame, text=message[1], bg='lightgrey', wraplength=300)
            content_label.pack(anchor='w')
            
            copy_button = tk.Button(message_frame, text="Копировать", command=lambda msg=message[1]: copy_to_clipboard(msg))
            copy_button.pack(anchor='w', pady=2)


        if message[3]:
            file_name = os.path.basename(message[3])

            def download_file(path=message[3]):
                if os.path.exists(path):
                    save_path = filedialog.asksaveasfilename(initialfile=file_name)
                    if save_path:
                        shutil.copy(path, save_path)
                        messagebox.showinfo("Успех", f"Файл сохранен: {save_path}")
                else:
                    messagebox.showerror("Ошибка", "Файл не найден.")

            file_button = tk.Button(message_frame, text=f"Скачать файл: {file_name}", command=download_file)
            file_button.pack(anchor='w')

def start_chat():
    receiver_input = simpledialog.askstring("Начать чат", "Введите ID или имя собеседника:")
    if receiver_input:
        receiver = find_user(receiver_input)
        if receiver:
            receiver_id = receiver[0]
            open_chat_window(receiver_id)
        else:
            messagebox.showerror("Ошибка", "Пользователь не найден.")

def auto_login():
    user_id, username = get_current_user()
    if user_id:
        global current_user_id
        global current_username
        current_user_id = user_id
        current_username = username
        set_current_user(user_id, username)
        update_ui_after_login()

def open_profile_section():
    clear_content_frame()
    tk.Label(content_frame, text="Профиль пользователя", font=("Arial", 16)).pack(pady=20)
    tk.Label(content_frame, text=f"ID пользователя: {current_user_id}", font=("Arial", 14)).pack(pady=10)
    tk.Label(content_frame, text=f"Имя пользователя: {current_username}", font=("Arial", 14)).pack(pady=10)

def open_settings_section():
    clear_content_frame()
    tk.Label(content_frame, text="Настройки пользователя", font=("Arial", 16)).pack(pady=20)

    tk.Label(content_frame, text="Изменить логин:").pack(pady=10)
    new_username_entry = tk.Entry(content_frame, width=30)
    new_username_entry.pack(pady=5)

    tk.Label(content_frame, text="Изменить пароль:").pack(pady=10)
    new_password_entry = tk.Entry(content_frame, width=30, show="*")
    new_password_entry.pack(pady=5)

    def save_changes():
        new_username = new_username_entry.get().strip()
        new_password = new_password_entry.get().strip()
        if new_username or new_password:
            update_user_details(current_user_id, new_username=new_username, new_password=new_password)
            if new_username:
                set_current_user(current_user_id, new_username)
            messagebox.showinfo("Успех", "Изменения сохранены.")
        else:
            messagebox.showerror("Ошибка", "Вы не ввели ни логин, ни пароль.")

    save_button = tk.Button(content_frame, text="Сохранить изменения", command=save_changes)
    save_button.pack(pady=10)






def delete_chat(peer_id):

    if messagebox.askyesno("Подтверждение", f"Вы действительно хотите удалить чат с пользователем {peer_id}?"):
        conn = create_connection()
        cursor = conn.cursor()
        cursor.execute('''
            DELETE FROM messages 
            WHERE (sender_id = ? AND receiver_id = ?) 
               OR (sender_id = ? AND receiver_id = ?);
        ''', (current_user_id, peer_id, peer_id, current_user_id))
        conn.commit()
        conn.close()
        messagebox.showinfo("Успех", "Чат был успешно удален.")
        show_chat_section() 

def show_chat_options():
    clear_content_frame()
    tk.Label(content_frame, text="Чаты", font=("Arial", 16)).pack(pady=10)

    start_chat_button = tk.Button(content_frame, text="Начать новый чат", command=start_chat)
    start_chat_button.pack(pady=5)

    create_group_button = tk.Button(content_frame, text="Создать новый групповой чат", command=create_new_group_window)
    create_group_button.pack(pady=5)

def show_chat_section():
    clear_content_frame()
    tk.Label(content_frame, text="Раздел 'Чат'", font=("Arial", 16)).pack(pady=10)
    previous_chats = get_previous_chats(current_user_id)
    
    if previous_chats:
        tk.Label(content_frame, text="Предыдущие чаты:", font=("Arial", 14)).pack(pady=5)
        
        chats_container = tk.Frame(content_frame)
        chats_container.pack(pady=5, fill=tk.BOTH, expand=True)
        
        chats_container.columnconfigure(0, weight=1)  
        chats_container.columnconfigure(1, weight=0)  
        chats_container.columnconfigure(2, weight=1)  
        
        for chat_partner_id in previous_chats:
            user = get_user_by_id(chat_partner_id)
            partner_name = user[1] if user else f"Пользователь {chat_partner_id}"
    
            chat_frame = tk.Frame(chats_container)
            chat_frame.grid(row=previous_chats.index(chat_partner_id), column=1, pady=5, sticky="ew")
            
            chat_frame.columnconfigure(0, weight=1)  
            chat_frame.columnconfigure(1, weight=0)  
            chat_frame.columnconfigure(2, weight=0)  
            chat_frame.columnconfigure(3, weight=1)  
    
            partner_button = tk.Button(chat_frame, text=f"{partner_name}", command=lambda partner_id=chat_partner_id: open_chat_window(partner_id))
            partner_button.grid(row=0, column=1, padx=(0, 10), sticky="e")
    
            delete_button = tk.Button(chat_frame, text="Удалить", command=lambda partner_id=chat_partner_id: delete_chat(partner_id))
            delete_button.grid(row=0, column=2, sticky="w")
    else:
        tk.Label(content_frame, text="У вас нет предыдущих чатов.", font=("Arial", 12)).pack(pady=5)
    
    start_chat_button = tk.Button(content_frame, text="Начать новый чат", command=start_chat)
    start_chat_button.pack(pady=5)

def clear_content_frame():
    for widget in content_frame.winfo_children():
        widget.pack_forget()

def attach_file(label):
    global selected_file_path
    file_path = filedialog.askopenfilename()
    if file_path:
        selected_file_path = file_path
        label.config(text=f"Прикреплен файл: {os.path.basename(file_path)}")
    else:
        selected_file_path = None
        label.config(text="Нет прикреплений")

def attach_chat_file(label):
    global selected_chat_file_path
    file_path = filedialog.askopenfilename()
    if file_path:
        selected_chat_file_path = file_path
        label.config(text=f"Прикреплен файл: {os.path.basename(file_path)}")
    else:
        selected_chat_file_path = None
        label.config(text="Прикрепления: Нет")

def clear_attachments():
    global selected_file_path
    selected_file_path = None

def clear_chat_attachments():
    global selected_chat_file_path
    selected_chat_file_path = None

def copy_to_clipboard(text):
    pyperclip.copy(text)
    

def display_message(listbox, message):
    display_text = f"{message[2]}: "
    sender = "Вы" if message[0] == current_user_id else f"Пользователь {message[0]}"
    display_text += f"{sender}: "
    if message[1]:
        display_text += message[1]

    listbox.insert(tk.END, display_text + "\n")

def get_previous_chats(user_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT receiver_id, MAX(timestamp) as last_msg_time
        FROM messages
        WHERE sender_id = ? AND receiver_type = 'user'
        AND sender_id != receiver_id  -- Исключить сообщения самому себе
        GROUP BY receiver_id
        UNION
        SELECT sender_id, MAX(timestamp) as last_msg_time
        FROM messages
        WHERE receiver_id = ? AND receiver_type = 'user'
        AND sender_id != receiver_id  -- Исключить сообщения самому себе
        GROUP BY sender_id
        ORDER BY last_msg_time DESC
    ''', (user_id, user_id))
    result = cursor.fetchall()
    conn.close()
    return [row[0] for row in result]

def get_user_by_id(user_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id, username FROM users WHERE id = ?;', (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

root = tk.Tk()
root.title("Приложение")
root.geometry("800x900")

content_frame = tk.Frame(root)

top_frame = tk.Frame(root)

left_frame = tk.Frame(top_frame)
left_frame.pack(side=tk.LEFT)

settings_button = tk.Button(left_frame, text="Настройки", command=open_settings_section)
settings_button.pack(padx=10, pady=5)

nav_frame = tk.Frame(top_frame)
nav_frame.pack(side=tk.LEFT, expand=True)

useful_info_button = tk.Button(nav_frame, text="Полезно узнать", command=lambda: useful_info.show_useful_info_section(content_frame))
chat_button = tk.Button(nav_frame, text="Чат", command=show_chat_section)
group_chat_button = tk.Button(nav_frame, text="Групповые чаты", command=show_group_chats)
video_call_menu = tk.Button(nav_frame, text="Видеозвонок", command=lambda: start_video_call(global_receiver_id))


useful_info_button.pack(side=tk.LEFT, padx=5, pady=5)
chat_button.pack(side=tk.LEFT, padx=5, pady=5)
group_chat_button.pack(side=tk.LEFT, padx=5, pady=5)
video_call_menu.pack(side=tk.LEFT, padx=5, pady=5)

right_frame = tk.Frame(top_frame)
right_frame.pack(side=tk.RIGHT)

profile_button = tk.Button(right_frame, text="Профиль", command=open_profile_section)
profile_button.pack(padx=10, pady=5)

logout_button = tk.Button(right_frame, text="Выход", command=logout)
logout_button.pack(padx=10, pady=5)

username_label = tk.Label(root, text="", font=("Arial", 14))

message_entry = tk.Entry(content_frame, width=50)

attachments_label = tk.Label(content_frame, text="Нет прикреплений")
attach_file_button = tk.Button(content_frame, text="Прикрепить файл", command=lambda: attach_file(attachments_label))
send_button = tk.Button(content_frame, text="Отправить сообщение", command=send_message)

messages_list = tk.Listbox(content_frame, width=70, height=15)

current_user_id = None
current_username = None
global_receiver_id = None
selected_file_path = None

selected_chat_file_path = None

login_button = tk.Button(root, text="Вход", command=login)
register_button = tk.Button(root, text="Регистрация", command=register)

username_label.pack(pady=10)
login_button.pack(pady=5)
register_button.pack(pady=5)

create_tables()
auto_login()

root.mainloop()