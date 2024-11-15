
import sqlite3
import tkinter as tk
from tkinter import messagebox, simpledialog

def create_connection():
    conn = sqlite3.connect('app_database.db')  
    return conn
# функции sql
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
            content TEXT NOT NULL,
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
    cursor.execute('INSERT INTO users (username) VALUES (?);', (username,))
    conn.commit()
    conn.close()

def authenticate_user(username):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM users WHERE username = ?;', (username,))
    user = cursor.fetchone()  
    conn.close()
    return user[0] if user else None  

def create_message(sender_id, receiver_id, content):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (sender_id, receiver_id, content) VALUES (?, ?, ?);', (sender_id, receiver_id, content))
    conn.commit()
    conn.close()

def load_messages(user_id):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT sender_id, content, timestamp FROM messages WHERE receiver_id = ?;', (user_id,))
    messages = cursor.fetchall()
    conn.close()
    return messages  

def send_message():
    receiver_id = simpledialog.askinteger("Отправка сообщения", "Введите ID получателя:")
    content = message_entry.get()
    if receiver_id and content:
        create_message(current_user_id, receiver_id, content)
        message_entry.delete(0, tk.END)
        refresh_messages()

def refresh_messages():
    messages = load_messages(current_user_id)
    messages_list.delete(0, tk.END)
    for message in messages:
        messages_list.insert(tk.END, f"{message[2]}: {message[1]}")

def login():
    username = simpledialog.askstring("Вход", "Введите имя пользователя:")
    user_id = authenticate_user(username)
    if user_id:
        global current_user_id
        current_user_id = user_id
        refresh_messages()
    else:
        messagebox.showerror("Ошибка", "Пользователь не найден.")

def register():
    username = simpledialog.askstring("Регистрация", "Введите новое имя пользователя:")
    create_user(username)

# Основное окно
root = tk.Tk()
root.title("Чат Приложение")

message_entry = tk.Entry(root, width=50)
message_entry.pack(pady=10)

send_button = tk.Button(root, text="Отправить сообщение", command=send_message)
send_button.pack(pady=5)

messages_list = tk.Listbox(root, width=50, height=15)
messages_list.pack(pady=10)

login_button = tk.Button(root, text="Вход", command=login)
login_button.pack(pady=5)

register_button = tk.Button(root, text="Регистрация", command=register)
register_button.pack(pady=5)

current_user_id = None  

create_tables()

root.mainloop()
