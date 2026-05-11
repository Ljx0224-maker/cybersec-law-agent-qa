#用智谱大模型重构本地向量库，接入智谱专为中文优化的 embedding-3 模型。它能精准理解“网络运营者”、“日志留存”这些专业法律词汇的深层语义。
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma  
import shutil
import os

# ⚠️请替换为你自己的真实信息
ZHIPU_API_KEY = "727d6d03b7f7476083c38633fd768d88.W1QqCdjuBks6sZMk"

print("--- 启动高精度向量知识库重构 (带数据清洗) ---")

print("正在读取并清洗《网络安全法》文本...")
with open("./data/cybersecurity_law.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()

# ⚡️ 核心修复：把所有导致断句的换行符替换掉，让文本变成连贯的长字符串
clean_text = raw_text.replace('\n', '')
documents = [Document(page_content=clean_text)]

print("正在切分文本...")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,       # 🌟 优化1：把容量从 300 放大到 500，足以装下一整个长法条
    chunk_overlap=100,    # 增加重叠度，防止边缘丢失
    separators=["。", "！", "？"] # 🌟 优化2：【极其关键】删掉分号 "；"！绝不允许把一条法律从中间切断！
)
chunks = text_splitter.split_documents(documents)

print("正在连接智谱 embedding-3 模型...")
embeddings = OpenAIEmbeddings(
    model="embedding-3",
    openai_api_key=ZHIPU_API_KEY,
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
)

# 为了防止数据污染，每次建库前先清空旧文件夹
if os.path.exists("./chroma_db_v2"):
    shutil.rmtree("./chroma_db_v2")

print("正在生成向量并存入新的本地数据库 (chroma_db_v2) ...")
db = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db_v2", 
    collection_name="cyber_law_collection_v2"
)

print("\n🎉 升级完成！带有智谱血统、且经过完美清洗的高精度向量数据库构建成功！")