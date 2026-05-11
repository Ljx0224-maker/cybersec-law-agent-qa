#FAISS建库
import os
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# 导入预处理函数
from data_process.preprocess_law import parse_cybersecurity_law

# ⚠️ 请替换为你自己的真实信息
ZHIPU_API_KEY = "727d6d03b7f7476083c38633fd768d88.W1QqCdjuBks6sZMk"

print("--- 启动 V3 终极高精度建库 (更换底层引擎为 FAISS) ---")

chunks = parse_cybersecurity_law("./data/cybersecurity_law.txt")
documents = [Document(page_content=chunk) for chunk in chunks]

embeddings = OpenAIEmbeddings(
    model="embedding-3",
    openai_api_key=ZHIPU_API_KEY,
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
)

print("正在调用智谱 API 并将数据写入 FAISS 向量库...")

try:
    # 🌟 智谱 API 限制单次最多 64 条，所以我们极其优雅地分两批送给 FAISS
    # 第一批：前 50 条
    db = FAISS.from_documents(documents[:50], embeddings)
    print("✅ 前 50 条向量化并入库成功！")
    
    # 第二批：剩下的所有条
    if len(documents) > 50:
        db.add_documents(documents[50:])
        print("✅ 剩余法条向量化并入库成功！")
        
    # 保存到本地文件夹 faiss_db_v3
    db.save_local("./faiss_db_v3")
    print("\n🎉 FAISS 向量库构建成功！彻底告别闪退！")

except Exception as e:
    print(f"❌ 发生错误: {e}")