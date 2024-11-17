import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
from PIL import Image, ImageTk
import os
import shutil
import time

def create_connection():
    conn = sqlite3.connect('app_database.db')
    return conn

def create_tables():
    conn = create_connection()
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE
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
            FOREIGN KEY (sender_id) REFERENCES users(id),
            FOREIGN KEY (receiver_id) REFERENCES users(id)
        );
    ''')

    conn.commit()
    conn.close()

def create_user(username):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username) VALUES (?);', (username,))
        conn.commit()
        messagebox.showinfo("Успех", "Пользователь успешно зарегистрирован.")
        user_id = cursor.lastrowid
        set_current_user(user_id, username)
        update_ui_after_login()
    except sqlite3.IntegrityError:
        messagebox.showerror("Ошибка", "Имя пользователя уже существует.")
    finally:
        conn.close()

def authenticate_user(username):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?;', (username,))
    user = cursor.fetchone()
    conn.close()
    return user[0] if user else None

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
    cursor.execute('''
        INSERT INTO messages (sender_id, receiver_id, content, file_path, image_path)
        VALUES (?, ?, ?, ?, ?);
    ''', (sender_id, receiver_id, content, file_path, image_path))
    conn.commit()
    conn.close()

def load_messages(user_id, chat_with_id=None):
    conn = create_connection()
    cursor = conn.cursor()
    if chat_with_id:
        cursor.execute('''
            SELECT sender_id, content, timestamp, file_path, image_path 
            FROM messages 
            WHERE (sender_id = ? AND receiver_id = ?) OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp;
        ''', (user_id, chat_with_id, chat_with_id, user_id))
    else:
        cursor.execute('SELECT sender_id, content, timestamp, file_path, image_path FROM messages WHERE receiver_id = ? ORDER BY timestamp;', (user_id,))
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
            if receiver_id and (content or selected_file_path or selected_image_path):
                file_destination = None
                image_destination = None

                if selected_file_path:
                    if not os.path.exists('files'):
                        os.makedirs('files')
                    unique_filename = f"{current_user_id}_{int(time.time())}_{os.path.basename(selected_file_path)}"
                    file_destination = os.path.join('files', unique_filename)
                    shutil.copy(selected_file_path, file_destination)

                if selected_image_path:
                    if not os.path.exists('images'):
                        os.makedirs('images')
                    unique_imagename = f"{current_user_id}_{int(time.time())}_{os.path.basename(selected_image_path)}"
                    image_destination = os.path.join('images', unique_imagename)
                    shutil.copy(selected_image_path, image_destination)

                create_message(current_user_id, receiver_id, content, file_destination, image_destination)
                message_entry.delete(0, tk.END)
                clear_attachments()
                attachments_label.config(text="Прикрепления: Нет")
                refresh_messages()
            else:
                messagebox.showerror("Ошибка", "Нельзя отправить пустое сообщение без файла или изображения.")
        else:
            messagebox.showerror("Ошибка", "Пользователь не найден.")

def refresh_messages():
    messages = load_messages(current_user_id)
    messages_list.delete(0, tk.END)
    for message in messages:
        display_message(messages_list, message)

def login():
    username = simpledialog.askstring("Вход", "Введите имя пользователя:")
    if username:
        user_id = authenticate_user(username)
        if user_id:
            set_current_user(user_id, username)
            update_ui_after_login()
        else:
            messagebox.showerror("Ошибка", "Пользователь не найден.")

def register():
    register_window = tk.Toplevel(root)
    register_window.title("Регистрация пользователя")
    register_window.geometry("300x150")

    tk.Label(register_window, text="Имя пользователя:").pack(pady=10)
    username_entry = tk.Entry(register_window, width=30)
    username_entry.pack(pady=5)

    def submit_registration():
        username = username_entry.get().strip()
        if username:
            create_user(username)
            register_window.destroy()
        else:
            messagebox.showerror("Ошибка", "Имя пользователя не может быть пустым.")

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

def update_ui_after_login():
    login_button.pack_forget()
    register_button.pack_forget()
    top_frame.pack(side=tk.TOP, fill=tk.X)
    content_frame.pack(fill=tk.BOTH, expand=True)
    show_news_section()

def update_ui_after_logout():
    top_frame.pack_forget()
    content_frame.pack_forget()
    username_label.config(text="")
    login_button.pack(pady=5)
    register_button.pack(pady=5)

def open_chat_window(receiver_id):
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

    chat_attachments_label = tk.Label(chat_window, text="Прикрепления: Нет")
    chat_attachments_label.pack(pady=5)

    chat_attach_file_button = tk.Button(chat_window, text="Прикрепить файл", command=lambda: attach_file(chat_attachments_label))
    chat_attach_file_button.pack(pady=5)

    def send_chat_message():
        content = chat_message_entry.get()
        if content or selected_file_path or selected_image_path:
            file_destination = None
            image_destination = None

            if selected_file_path:
                if not os.path.exists('files'):
                    os.makedirs('files')
                unique_filename = f"{current_user_id}_{int(time.time())}_{os.path.basename(selected_file_path)}"
                file_destination = os.path.join('files', unique_filename)
                shutil.copy(selected_file_path, file_destination)

            if selected_image_path:
                if not os.path.exists('images'):
                    os.makedirs('images')
                unique_imagename = f"{current_user_id}_{int(time.time())}_{os.path.basename(selected_image_path)}"
                image_destination = os.path.join('images', unique_imagename)
                shutil.copy(selected_image_path, image_destination)

            create_message(current_user_id, receiver_id, content, file_destination, image_destination)
            chat_message_entry.delete(0, tk.END)
            clear_attachments()
            chat_attachments_label.config(text="Прикрепления: Нет")
            refresh_chat_messages(chat_scrollable_frame, receiver_id)
        else:
            messagebox.showerror("Ошибка", "Нельзя отправить пустое сообщение без файла или изображения.")

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

        if message[4]:
            img = Image.open(message[4])
            img.thumbnail((200, 200))
            photo = ImageTk.PhotoImage(img)
            img_label = tk.Label(message_frame, image=photo)
            img_label.image = photo
            img_label.pack(anchor='w')

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
    tk.Label(content_frame, text="Настройки приложения", font=("Arial", 16)).pack(pady=20)
    # Добавьте здесь элементы настроек по необходимости

def show_news_section():
    clear_content_frame()
    tk.Label(content_frame, text="Новости", font=("Arial", 16)).pack(pady=20)
    news = [
        "Добро пожаловать в приложение!",
        "Следите за обновлениями."
    ]
    scrollbar = tk.Scrollbar(content_frame)
    news_text = tk.Text(content_frame, wrap=tk.WORD, yscrollcommand=scrollbar.set, font=("Arial", 14))
    scrollbar.config(command=news_text.yview)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    for item in news:
        news_text.insert(tk.END, item + "\n\n")
    news_text.config(state=tk.DISABLED)  # Сделать текст не редактируемым
    news_text.pack(expand=True, fill=tk.BOTH)

def show_study_section():
    clear_content_frame()
    tk.Label(content_frame, text="Раздел 'Учеба'", font=("Arial", 16)).pack(pady=20)

def show_schedule_section():
    clear_content_frame()
    tk.Label(content_frame, text="Раздел 'Расписание'", font=("Arial", 16)).pack(pady=20)

def show_useful_info_section():
    clear_content_frame()
    tk.Label(content_frame, text="Полезная информация", font=("Arial", 16)).pack(pady=20)
    useful_info = "Здесь вы можете найти полезную информацию."

    tk.Label(content_frame, text=useful_info, font=("Arial", 12)).pack(pady=10)

def show_chat_section():
    clear_content_frame()
    tk.Label(content_frame, text="Раздел 'Чат'", font=("Arial", 16)).pack(pady=10)
    # Отображение списка предыдущих чатов
    previous_chats = get_previous_chats(current_user_id)
    if previous_chats:
        tk.Label(content_frame, text="Предыдущие чаты:", font=("Arial", 14)).pack(pady=5)
        for chat_partner_id in previous_chats:
            user = get_user_by_id(chat_partner_id)
            partner_name = user[1] if user else f"Пользователь {chat_partner_id}"
            def open_chat_with_partner(partner_id=chat_partner_id):
                open_chat_window(partner_id)
            partner_button = tk.Button(content_frame, text=f"Чат с {partner_name}", command=open_chat_with_partner)
            partner_button.pack(pady=2)
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
        label.config(text="Прикрепления: Нет")

def attach_image(label):
    global selected_image_path
    image_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.gif")])
    if image_path:
        selected_image_path = image_path
        label.config(text=f"Прикреплено изображение: {os.path.basename(image_path)}")
    else:
        selected_image_path = None
        label.config(text="Прикрепления: Нет")

def clear_attachments():
    global selected_file_path
    global selected_image_path
    selected_file_path = None
    selected_image_path = None

def display_message(listbox, message):
    display_text = f"{message[2]}: "
    sender = "Вы" if message[0] == current_user_id else f"Пользователь {message[0]}"
    display_text += f"{sender}: "
    if message[1]:
        display_text += message[1]

    listbox.insert(tk.END, display_text + "\n")

    if message[4]:
        img = Image.open(message[4])
        img.thumbnail((100, 100))
        photo = ImageTk.PhotoImage(img)
        listbox.image_create(tk.END, image=photo)
        listbox.insert(tk.END, "\n")

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

        listbox.insert(tk.END, f"Скачать файл: {file_name}\n")

def open_file(path):
    if os.path.exists(path):
        os.startfile(path)
    else:
        messagebox.showerror("Ошибка", "Файл не найден.")

def get_previous_chats(user_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT receiver_id, MAX(timestamp) as last_msg_time
        FROM messages
        WHERE sender_id = ?
        GROUP BY receiver_id
        UNION
        SELECT sender_id, MAX(timestamp) as last_msg_time
        FROM messages
        WHERE receiver_id = ?
        GROUP BY sender_id
        ORDER BY last_msg_time ASC
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
root.title("Чат Приложение")
root.geometry("600x700")

content_frame = tk.Frame(root)

top_frame = tk.Frame(root)

left_frame = tk.Frame(top_frame)
left_frame.pack(side=tk.LEFT)

settings_button = tk.Button(left_frame, text="Настройки", command=open_settings_section)
settings_button.pack(padx=10, pady=5)

nav_frame = tk.Frame(top_frame)
nav_frame.pack(side=tk.LEFT, expand=True)

study_button = tk.Button(nav_frame, text="Учеба", command=show_study_section)
schedule_button = tk.Button(nav_frame, text="Расписание", command=show_schedule_section)
useful_info_button = tk.Button(nav_frame, text="Полезно узнать", command=show_useful_info_section)
chat_button = tk.Button(nav_frame, text="Чат", command=show_chat_section)

study_button.pack(side=tk.LEFT, padx=5, pady=5)
schedule_button.pack(side=tk.LEFT, padx=5, pady=5)
useful_info_button.pack(side=tk.LEFT, padx=5, pady=5)
chat_button.pack(side=tk.LEFT, padx=5, pady=5)

right_frame = tk.Frame(top_frame)
right_frame.pack(side=tk.RIGHT)

profile_button = tk.Button(right_frame, text="Профиль", command=open_profile_section)
profile_button.pack(padx=10, pady=5)

logout_button = tk.Button(right_frame, text="Выход", command=logout)
logout_button.pack(padx=10, pady=5)

username_label = tk.Label(root, text="", font=("Arial", 14))

message_entry = tk.Entry(content_frame, width=50)

attachments_label = tk.Label(content_frame, text="Прикрепления: Нет")
attach_file_button = tk.Button(content_frame, text="Прикрепить файл", command=lambda: attach_file(attachments_label))

send_button = tk.Button(content_frame, text="Отправить сообщение", command=send_message)

messages_list = tk.Listbox(content_frame, width=70, height=15)

current_user_id = None
current_username = None

selected_file_path = None
selected_image_path = None

login_button = tk.Button(root, text="Вход", command=login)
register_button = tk.Button(root, text="Регистрация", command=register)

username_label.pack(pady=10)
login_button.pack(pady=5)
register_button.pack(pady=5)

create_tables()
auto_login()

root.mainloop()