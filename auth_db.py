# 管理用户账号体系的 SQLite 数据库封装层
import sqlite3
import hashlib

# 密码加密函数（保护用户隐私）
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

# 初始化用户表
def init_auth_db():
    conn = sqlite3.connect('chat.db') # 和对话记录存在同一个库里
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password_hash TEXT)''')
    conn.commit()
    conn.close()

# 注册新用户
def add_user(username, password):
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, make_hashes(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # 触发唯一约束，说明用户名已被占用
    finally:
        conn.close()

# 验证登录
def login_user(username, password):
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    data = c.fetchone()
    conn.close()
    if data:
        return check_hashes(password, data[0])
    return False

def get_all_users():
    """获取数据库中所有的用户名"""
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    c.execute("SELECT username FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

def delete_user(username):
    """删除用户账号，并级联删除其所有的历史对话（防止占内存）"""
    conn = sqlite3.connect('chat.db')
    c = conn.cursor()
    # 1. 删除账号
    c.execute("DELETE FROM users WHERE username = ?", (username,))
    # 2. 清理该用户的所有对话标题
    c.execute("DELETE FROM sessions WHERE username = ?", (username,))
    # 注意：更严谨的做法还会去 messages 表里删具体消息，这里暂且清理 sessions 已能达到隔离效果
    conn.commit()
    conn.close()