# 负责建表、读写对话历史、删除、重命名，管理用户的会话（Session）和具体聊天气泡（Messages）的 SQLite 数据库封装层
import sqlite3
import uuid
import json
from datetime import datetime

DB_FILE = "chat.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # 1. 初始化 sessions 表时，加入 username 字段
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id TEXT PRIMARY KEY, username TEXT, title TEXT, created_at TIMESTAMP)''')
    
    # 兼容老数据魔法
    try:
        c.execute("ALTER TABLE sessions ADD COLUMN username TEXT")
    except sqlite3.OperationalError:
        pass 

    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  session_id TEXT, 
                  role TEXT, 
                  content TEXT, 
                  keywords TEXT, 
                  graph_info TEXT, 
                  vector_info TEXT,
                  created_at TIMESTAMP)''')
    conn.commit()
    conn.close()

def create_new_session(username, title="新对话"):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    session_id = str(uuid.uuid4())
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    # 插入数据时，把 username 一起插进去
    c.execute("INSERT INTO sessions (id, username, title, created_at) VALUES (?, ?, ?, ?)", 
              (session_id, username, title, created_at))
    conn.commit()
    conn.close()
    return session_id

def save_message(session_id, role, content, keywords="", graph_info=None, vector_info=None):
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 将图谱和向量列表转换为 JSON 字符串，方便存入 SQLite
    graph_str = json.dumps(graph_info, ensure_ascii=False) if graph_info else "[]"
    vector_str = json.dumps(vector_info, ensure_ascii=False) if vector_info else "[]"
    
    # 处理 keywords 的数据类型
    if isinstance(keywords, list):
        keywords_str = ", ".join(keywords)
    else:
        keywords_str = str(keywords) if keywords else ""
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO messages (session_id, role, content, keywords, graph_info, vector_info, created_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (session_id, role, content, keywords_str, graph_str, vector_str, created_at))
    conn.commit()
    conn.close()

def get_all_sessions(username):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 查询时加入条件，并按时间倒序排列（最新的在最上面）
    c.execute("SELECT id, title FROM sessions WHERE username = ? ORDER BY created_at DESC", (username,))
    sessions = c.fetchall()
    conn.close()
    return sessions

def get_messages_by_session(session_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("SELECT role, content, keywords, graph_info, vector_info FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,))
    
    messages = []
    for row in cursor.fetchall():
        msg = {
            "role": row[0], 
            "content": row[1],
            "keywords": row[2] if row[2] else "",
            "graph_info": json.loads(row[3]) if row[3] else [],
            "vector_info": json.loads(row[4]) if row[4] else []
        }
        messages.append(msg)
        
    conn.close()
    return messages

def update_session_title(session_id, new_title):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET title = ? WHERE id = ?", (new_title, session_id)) # 🚨 修复：原先写成了 session_id = ?，但表里存的是 id
    conn.commit()
    conn.close()

def delete_session(session_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,)) # 🚨 修复：同样修正列名为 id
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()