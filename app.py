import streamlit as st
import base64 
import streamlit.components.v1 as components

from qa_agent import extract_keywords, extract_keywords_from_doc, search_graph_db, search_vector_with_reranker, generate_final_answer
from chat_db import init_db, create_new_session, save_message, get_all_sessions, get_messages_by_session, update_session_title, delete_session
from auth_db import init_auth_db, add_user, login_user, get_all_users, delete_user

st.set_page_config(page_title="网络安全法律领域AI问答系统", page_icon=":material/admin_panel_settings:", layout="wide", initial_sidebar_state="expanded")

# 全局 CSS 样式封装 (将所有美化代码集中管理)
def inject_custom_css():
    st.markdown("""
        <style>
        /* --- 1. 全局背景与字体 --- */
        .stApp { background-color: #f8f9fa; font-family: 'Inter', "Microsoft YaHei", sans-serif; }
        [data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
        
        /* --- 2. 聊天气泡内标题字号缩小 --- */
        .stChatMessage h1, .stChatMessage h2, .stChatMessage h3, .stChatMessage h4, .stChatMessage h5, .stChatMessage h6,
        [data-testid="stChatMessage"] h1, [data-testid="stChatMessage"] h2, [data-testid="stChatMessage"] h3, 
        [data-testid="stChatMessage"] h4, [data-testid="stChatMessage"] h5, [data-testid="stChatMessage"] h6 {
            font-size: 1.15rem !important; /* 强制统一设为偏小且温和的字号 */
            margin-top: 0.8rem !important; 
            margin-bottom: 0.4rem !important; 
            font-weight: 600 !important; 
            line-height: 1.4 !important;
        }
        
        /* --- 3. 自定义文件上传组件 (伪装成按钮) --- */
        [data-testid="stFileUploaderDropzoneInstructions"] { display: none !important; }
        [data-testid="stFileUploaderDropzone"] { border: none !important; background-color: transparent !important; padding: 0 !important; min-height: auto !important; }
        [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"] {
            width: 100% !important; font-size: 0 !important; padding: 0.5rem 1rem !important; border-radius: 12px !important; display: flex !important; align-items: center !important; justify-content: center !important; gap: 6px !important;
        }
        [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"]::before {
            content: ""; display: inline-block; width: 1.25rem; height: 1.25rem; background-color: currentColor;
            -webkit-mask: url("data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z'/%3E%3C/svg%3E") no-repeat center / contain;
            mask: url("data:image/svg+xml;charset=UTF-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M9 16h6v-6h4l-7-7-7 7h4zm-4 2h14v2H5z'/%3E%3C/svg%3E") no-repeat center / contain;
        }
        [data-testid="stFileUploaderDropzone"] [data-testid="stBaseButton-secondary"]::after { content: "上传文件"; font-size: 16px !important; font-weight: 500 !important; }
        
        /* --- 4. 原生 Chat 组件的深度定制 (白/蓝气泡) --- */
        [data-testid="stChatMessage"] { background-color: transparent !important; padding: 0.5rem 0 !important; }
        [data-testid="stChatMessage"] [data-testid="stChatMessageContent"] {
            background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 12px; padding: 15px 20px; margin: 0 15px; flex-grow: 1; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        [data-testid="stChatMessage"] [data-testid="stImage"] { border-radius: 50% !important; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        [data-testid="stChatMessage"]:has(.user-marker) { flex-direction: row-reverse; }
        [data-testid="stChatMessage"]:has(.user-marker) [data-testid="stChatMessageContent"] { background-color: #e3f2fd !important; border: 1px solid #bbdefb !important; }
        
        /* --- 5. 聊天界面排版与侧边栏控制 --- */     
        [data-testid="stSidebarCollapseButton"] { visibility: visible !important; opacity: 1 !important; display: flex !important; transition: all 0.3s ease; }
        [data-testid="stSidebarCollapseButton"] button { background-color: #f0f2f5 !important; color: #444746 !important; border-radius: 8px !important; width: 32px !important; height: 32px !important; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        [data-testid="stSidebarCollapseButton"] button:hover { background-color: #e2e5e9 !important; color: #1a73e8 !important; }
        
        /* --- 6. 按钮系统美化 (Primary/Secondary) --- */
        button[kind="primary"] { background-color: skyblue !important; color: white !important; border: none !important; border-radius: 8px !important; font-weight: bold !important; }
        button[kind="primary"]:hover { background-color: #5DADE2 !important; color: white !important; }
        [data-testid="stSidebar"] button[kind="secondary"] { border: 1px solid transparent !important; background-color: #f4f6f8 !important; border-radius: 12px !important; color: #444746 !important; font-weight: 500 !important; transition: all 0.3s ease !important; box-shadow: 0 1px 2px rgba(0,0,0,0.02) !important; }
        [data-testid="stSidebar"] button[kind="secondary"]:hover { background-color: #e8eaed !important; transform: translateY(-1px); box-shadow: 0 4px 8px rgba(0,0,0,0.05) !important; }
        [data-testid="stSidebar"] button[kind="primary"] { border-radius: 12px !important; border: none !important; box-shadow: 0 2px 6px rgba(135, 206, 250, 0.3) !important; }
        [data-testid="stSidebar"] .stColumn:nth-child(2) button { border-radius: 50% !important; background-color: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; }
        [data-testid="stSidebar"] .stColumn:nth-child(2) button:hover { background-color: #e8eaed !important; transform: scale(1.05); }
        
        /* --- 7. 顶栏固定标题与输入框 --- */
        .gemini-title-container { position: fixed; top: 0; left: 0; width: 100%; height: 50px; display: flex; align-items: center; justify-content: center; background-color: white; z-index: 90; }
        .gemini-text { font-family: "Inter", sans-serif; font-size: 1.1rem; font-weight: 500; color: #444746; }
        hr { display: none !important; }
        header[data-testid="stHeader"] { background-color: transparent !important; }
        .stChatInputContainer { border-radius: 25px !important; background-color: #ffffff !important; box-shadow: 0 2px 10px rgba(0,0,0,0.05) !important; }
        [data-testid="stChatInput"] > div { border: 1px solid #e0e4e9 !important; border-radius: 25px !important; transition: all 0.3s ease !important; }
        [data-testid="stChatInput"] > div:focus-within { border-color: skyblue !important; box-shadow: 0 0 0 1.5px skyblue !important; }
        [data-testid="stChatInput"] > div:focus-within button svg { fill: skyblue !important; color: skyblue !important; }
        </style>
    """, unsafe_allow_html=True)

# 状态初始化与数据库连接
def init_session_state():
    """初始化所有的页面状态变量"""
    if "page" not in st.session_state: st.session_state.page = "home"
    if "current_session_id" not in st.session_state: st.session_state.current_session_id = None
    if "messages" not in st.session_state: st.session_state.messages = []
    if "logged_in" not in st.session_state: st.session_state.logged_in = False
    if "username" not in st.session_state: st.session_state.username = ""

# 执行初始化
inject_custom_css()
init_db()
init_auth_db()
init_session_state()

# 核心辅助函数与交互弹窗
@st.cache_data
def get_image_base64(image_path):
    """将本地图片转码供网页显示"""
    try:
        with open(image_path, "rb") as img_file:
            return "data:image/jpeg;base64," + base64.b64encode(img_file.read()).decode()
    except Exception: return None

def start_new_chat():
    """新建对话并清理旧文件"""
    new_id = create_new_session(st.session_state.username, "新对话")
    st.session_state.current_session_id = new_id
    welcome_text = f"你好，{st.session_state.username}！需要我为你解答什么有关《网络安全法》的问题呢？"
    st.session_state.messages = [{"role": "assistant", "content": welcome_text}]
    save_message(new_id, "assistant", welcome_text)
    if "doc_uploader" in st.session_state: del st.session_state["doc_uploader"]

def load_history_chat(session_id):
    """加载历史对话并清理旧文件"""
    st.session_state.current_session_id = session_id
    st.session_state.messages = get_messages_by_session(session_id)
    if "doc_uploader" in st.session_state: del st.session_state["doc_uploader"]

@st.dialog("登录与注册")
def login_register_dialog():
    """控制登录、注册与管理员的弹窗"""
    tab_login, tab_register, tab_admin = st.tabs(["登录账号", "注册新账号", "管理员入口"])
    
    with tab_login:
        login_username = st.text_input("用户名", key="login_user")
        login_password = st.text_input("密码", type="password", key="login_pass")
        if st.button("确认登录", type="primary", use_container_width=True):
            if login_username and login_password:
                if login_user(login_username, login_password):
                    st.session_state.logged_in = True
                    st.session_state.username = login_username
                    st.session_state.page = "chat"
                    if st.session_state.current_session_id is None: start_new_chat()
                    st.rerun() 
                else: st.error("用户名或密码错误！没有账号请先注册")
            else: st.warning("请填写完整用户名和密码！")
            
    with tab_register:
        reg_username = st.text_input("设置用户名", key="reg_user")
        reg_password = st.text_input("设置密码", type="password", key="reg_pass")
        reg_password_confirm = st.text_input("确认密码", type="password", key="reg_pass_confirm")
        if st.button("立即注册", type="primary", use_container_width=True):
            if reg_password != reg_password_confirm: st.warning("两次输入的密码不一致！")
            elif not reg_username or not reg_password: st.warning("用户名和密码不能为空！")
            else:
                if add_user(reg_username, reg_password): st.success("注册成功！请切换左侧标签页进行登录。")
                else: st.error("该用户名已被注册，请换一个重试！")
                
    with tab_admin:
        st.info("此通道仅供系统管理员使用")
        admin_user = st.text_input("管理员账号", value="admin", disabled=True) 
        admin_pass = st.text_input("管理员超级密码", type="password", key="admin_pass")
        if st.button("进入控制台", type="primary", use_container_width=True):
            if admin_pass == "admin123":
                st.session_state.logged_in = True; st.session_state.username = "admin"
                st.session_state.page = "admin"; st.rerun()
            else: st.error("管理员密码错误，无权访问！")

@st.dialog("管理对话")
def manage_session_dialog(sess_id, current_title):
    """修改或删除对话标题的弹窗"""
    new_name = st.text_input("重命名", value=current_title, key=f"rename_input_{sess_id}", label_visibility="collapsed")
    c1, c2 = st.columns(2)
    with c1:
        if st.button(":material/save: 保存", use_container_width=True):
            update_session_title(sess_id, new_name); st.rerun()
    with c2:
        if st.button(":material/delete: 删除", use_container_width=True):
            delete_session(sess_id)
            if st.session_state.current_session_id == sess_id:
                st.session_state.current_session_id = None; st.session_state.messages = []
            st.rerun()

# 页面路由与主渲染逻辑
# 页面 1：系统首页 (Home)
if st.session_state.page == "home":
    st.markdown("<h1 style='text-align: center; color: #1E1E1E;'>基于智能体的网络安全法律领域知识问答系统</h1>", unsafe_allow_html=True)
    st.write("---")
    col_left, col_right = st.columns(2, gap="large")
    
    with col_left:
        st.markdown("### :material/search: 系统介绍")
        st.markdown("""
        <div style="background-color: #f0f2f5; padding: 1.2rem; border-radius: 8px; color: #444746; line-height: 1.6;">
            本系统致力于打破法律专业壁垒。通过深度融合大语言模型（GLM-5）与双路召回技术：
            <ul style="margin-top: 10px; margin-bottom: 10px;">
                <li><b>知识图谱 (Neo4j)</b>：精准解析法条之间的复杂关联与处罚逻辑。</li>
                <li><b>向量检索 (FAISS)</b>：语义化匹配最相关的法律条文原文。</li>
            </ul>
            将晦涩的法律文本转化为通俗易懂的专业解答，为企业合规与个人维权提供高效、可靠的智能法律援助。
        </div>
        """, unsafe_allow_html=True)
    
    with col_right:
        st.markdown("### :material/assistant_navigation: 使用指南")
        st.markdown("您可以点击下方开始体验的按钮进入对话，以下是推荐的提问场景：")
        with st.expander(":material/dataset_linked: 基础概念查询", expanded=True): st.caption("“到底什么是‘网络运营者’？它包含哪些机构？”")
        with st.expander(":material/move_down: 法律责任推理", expanded=False): st.caption("“关键信息基础设施的具体保护范围和安全保护办法由谁制定？”")
        with st.expander(":material/swipe_up: 复杂场景咨询", expanded=False): st.caption("“公司泄露数据并决定隐瞒，主管人员最高罚多少钱？”")
        with st.expander(":material/plagiarism: 智能合规审查", expanded=False): st.caption("“在对话界面的左侧边栏上传企业的规章制度文件（txt），然后提问：‘请严格审查这份文件是否合格，若不合格存在哪些违法条款？’”")

    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1, 1])
    with c2:
        if st.button("开始体验", use_container_width=True, type="primary"):
            if st.session_state.logged_in:
                st.session_state.page = "chat"
                if st.session_state.current_session_id is None: start_new_chat()
                st.rerun()
            else:
                login_register_dialog()

# 管理员控制台
elif st.session_state.page == "admin":
    col_title, col_exit = st.columns([8, 1])
    with col_title: st.markdown("<h2 style='color: #1E1E1E;'>系统管理员控制台</h2>", unsafe_allow_html=True)
    with col_exit:
        if st.button("退出登录", icon=":material/logout:", use_container_width=True):
            st.session_state.logged_in = False; st.session_state.username = ""; st.session_state.current_session_id = None; st.session_state.messages = []; st.session_state.page = "home"
            if "doc_uploader" in st.session_state: del st.session_state["doc_uploader"] 
            st.rerun()
    
    tab_manage, tab_monitor = st.tabs(["用户账号管理", "用户对话监控"])
    with tab_manage:
        all_users = get_all_users()
        st.subheader(f"当前系统总注册人数：{len(all_users)}")
        for u in all_users:
            if u == "admin": continue
            c1, c2 = st.columns([4, 1])
            with c1: st.markdown(f"用户名: **{u}**")
            with c2:
                if st.button("注销该账号", key=f"del_{u}", type="primary"):
                    delete_user(u); st.success(f"已永久删除用户 {u} 及其会话记录！"); st.rerun()
                    
    with tab_monitor:
        all_users = get_all_users()
        selected_user = st.selectbox("请选择要查看的用户：", [u for u in all_users if u != "admin"])
        if selected_user:
            user_sessions = get_all_sessions(selected_user)
            if not user_sessions: st.info(f"用户 {selected_user} 暂无任何对话记录。")
            else:
                selected_session = st.selectbox("请选择要查看的对话：", user_sessions, format_func=lambda x: f"{x[1]} (ID: {x[0][:8]}...)")
                if selected_session:
                    st.markdown(f"#### 对话记录详情<br>", unsafe_allow_html=True)
                    messages = get_messages_by_session(selected_session[0])
                    for msg in messages:
                        if msg["role"] == "user": st.info(f"**用户:** {msg['content']}")
                        else: st.success(f"**系统:** {msg['content']}")

# 对话主界面
elif st.session_state.page == "chat":
    st.markdown("<style>.block-container { max-width: 850px !important; margin: 0 auto !important; padding-top: 4rem !important; }</style>", unsafe_allow_html=True)
    # --- 3.1 侧边栏布局 ---
    with st.sidebar:
        if st.button("返回首页 ", icon=":material/home:", use_container_width=True):
            st.session_state.page = "home"; st.rerun()
        if st.button("发起新对话", icon=":material/add:", use_container_width=True):
            start_new_chat(); st.rerun()
        if st.button("退出登录", icon=":material/logout:", use_container_width=True):
            st.session_state.logged_in = False; st.session_state.username = ""; st.session_state.current_session_id = None; st.session_state.messages = []; st.session_state.page = "home"; st.rerun()

        st.subheader("合规审查区")
        uploader_key = f"doc_uploader_{st.session_state.current_session_id}"
        uploaded_doc = st.file_uploader("上传待审查文档 (txt格式)", type=["txt"], key=uploader_key)
        doc_content = ""
        if uploaded_doc is not None:
            doc_content = uploaded_doc.getvalue().decode("utf-8")
            st.success("文档已加载！请在右侧提问")
            
        st.divider()
        st.subheader("历史对话")
        history_sessions = get_all_sessions(st.session_state.username)
        if not history_sessions: st.caption("暂无历史对话")
        else:
            for sess_id, title in history_sessions:
                col1, col2 = st.columns([4, 1])
                with col1:
                    is_current = (sess_id == st.session_state.current_session_id)
                    btn_type = "primary" if is_current else "secondary"
                    if st.button(title, key=f"btn_{sess_id}", use_container_width=True, type=btn_type):
                        load_history_chat(sess_id); st.rerun()
                with col2:
                    if st.button("⋮", key=f"opt_{sess_id}", use_container_width=True): manage_session_dialog(sess_id, title)

    # --- 3.2 顶部静态装饰 ---
    st.markdown("""
        <div class="gemini-title-container"><span class="gemini-text">基于智能体的网络安全法律领域知识问答系统</span></div>
        <hr style='margin: 10px 0px 20px -45px; border: 0.5px solid #eee;'>
    """, unsafe_allow_html=True)

    ai_logo_url = get_image_base64("assets/ai_icon.jpg")
    user_logo_url = get_image_base64("assets/user_icon.jpg")
    chat_container = st.container()

    # --- 3.3 渲染历史聊天记录 ---
    with chat_container:
        for i, msg in enumerate(st.session_state.messages):
            if msg["role"] == "user":
                with st.chat_message("user", avatar=user_logo_url):
                    st.markdown("<span class='user-marker'></span>", unsafe_allow_html=True)
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant", avatar=ai_logo_url):
                    st.write(msg["content"])
                    if msg.get("keywords"):
                        with st.expander("查看 AI 底层检索与推理黑盒 (历史记录)"):
                            st.write(f"**提取关键词**: `{msg['keywords']}`")
                            st.write("**图谱命中链路 (Neo4j)**:")
                            st.code("\n".join(msg['graph_info']) if msg['graph_info'] else "未检索到相关逻辑链", language="text")
                            st.write("**向量精排召回法条 (FAISS Top 3)**:")
                            st.info("\n\n".join(msg['vector_info']) if msg['vector_info'] else "未检索到相关法条")

    # --- 3.4 接收新问题并执行 RAG 生成 ---
    if prompt := st.chat_input("请在此输入您的法律问题..."):
        user_msg_count = len([m for m in st.session_state.messages if m["role"] == "user"])
        if user_msg_count == 0:
            update_session_title(st.session_state.current_session_id, prompt[:7])
            st.session_state.force_sidebar_refresh = True
        
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_message(st.session_state.current_session_id, "user", prompt)

        with chat_container:
            with st.chat_message("user", avatar=user_logo_url):
                st.markdown("<span class='user-marker'></span>", unsafe_allow_html=True); st.write(prompt)
            
            with st.status("引擎启动：正在执行多路召回与逻辑推理...", expanded=True) as status:
                if doc_content:
                    st.write("检测到合规审查文档，正在深度阅读并提取合规风险锚点...")
                    keywords = extract_keywords_from_doc(doc_content)
                    st.write(f"从文档中揪出高危关键词: `{keywords}`")
                    search_query = prompt + " " + " ".join(keywords)
                else:
                    st.write("正在提取用户提问关键词...")
                    keywords = extract_keywords(prompt)
                    st.write(f"提取成功: `{keywords}`")
                    search_query = prompt

                st.write("正在从 Neo4j 知识图谱中检索法律关联...")
                graph_info = search_graph_db(keywords)
                st.code("\n".join(graph_info) if graph_info else "未检索到相关逻辑链", language="text")
                
                st.write("正在调用 FAISS 向量库与 BGE 模型进行精排召回...")
                vector_info = search_vector_with_reranker(search_query, keywords)
                st.info("\n\n".join(vector_info) if vector_info else "未检索到相关法条")
                
                st.write("正在将检索结果输入大模型生成最终法律意见...")
                if doc_content:
                    enhanced_prompt = f"你是一名极其严谨的合规审查员。请严格依据下方系统检索出的【参考法条原文】，对【用户上传的待审查文档】进行分析，指出违规点。绝对不允许脱离给定的法条凭空捏造法律依据（严禁产生幻觉）！\n\n【用户上传的待审查文档】:\n{doc_content}\n\n【用户的具体问题】:\n{prompt}"
                else:
                    enhanced_prompt = prompt
                
                final_answer = generate_final_answer(enhanced_prompt, vector_info, graph_info)
                status.update(label="检索与推理完成，已生成法律顾问建议", state="complete", expanded=False)
                
            with st.chat_message("assistant", avatar=ai_logo_url):
                st.write(final_answer)

        ai_msg_data = {"role": "assistant", "content": final_answer, "keywords": keywords, "graph_info": graph_info, "vector_info": vector_info}
        st.session_state.messages.append(ai_msg_data)
        save_message(st.session_state.current_session_id, "assistant", final_answer, keywords, graph_info, vector_info)

        if st.session_state.get("force_sidebar_refresh", False):
            st.session_state.force_sidebar_refresh = False
            st.rerun()