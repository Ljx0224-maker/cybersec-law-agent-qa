import os
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
embeddings = OpenAIEmbeddings(model="embedding-3", openai_api_key=ZHIPU_API_KEY, openai_api_base="https://open.bigmodel.cn/api/paas/v4/")

print("正在加载本地向量库...")
db = FAISS.load_local("./faiss_db", embeddings, allow_dangerous_deserialization=True)

# 遍历文档仓库，揪出所有包含“【网络安全法”的旧片段 ID
ids_to_delete = []
for doc_id, doc in db.docstore._dict.items():
    if "【中华人民共和国网络安全法" in doc.page_content:
        ids_to_delete.append(doc_id)

# 执行删除并保存
if ids_to_delete:
    print(f"共发现 {len(ids_to_delete)} 条《网络安全法》旧数据，正在执行定向删除...")
    db.delete(ids_to_delete)
    db.save_local("./faiss_db")
    print("FAISS 向量库定向清除完毕！其他法律数据完好无损。")
else:
    print("未在向量库中找到相关的《网络安全法》数据。")