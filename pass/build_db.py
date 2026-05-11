#处理法律长文本并构建向量数据库
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import chromadb
import os

print("--- 开始构建法律知识库 ---")

# 1. 加载本地 txt 文本
file_path = "./data/cybersecurity_law.txt"
print(f"正在读取法律文本: {file_path}")
# 注意这里必须加 encoding="utf-8"，否则 Windows 下读取中文字符会报错
loader = TextLoader(file_path, encoding="utf-8")
documents = loader.load()

# 2. 对长文本进行“切片” (Chunking)
# 为什么切片？因为大模型一次性吃不下整本书，且切分后检索更精准。
print("正在使用 LangChain 对文本进行智能切片...")
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,       # 每块大约 300 个字符（适合法律条文的长度）
    chunk_overlap=50,     # 两块之间重叠 50 个字，防止把一句话从中间硬生生切断
    separators=["\n\n", "\n", "。", "；", "，", " "] # 优先按段落和句号切
)
chunks = text_splitter.split_documents(documents)
print(f"切片完成！整部法律被切分成了 {len(chunks)} 个文本块 (Chunks)。")

# 3. 初始化 ChromaDB 本地持久化数据库
print("正在连接/创建 ChromaDB 本地数据库...")
# 数据会保存在项目目录下的 chroma_db 文件夹中
client = chromadb.PersistentClient(path="./chroma_db")

# 创建一个集合（相当于关系型数据库里的一张表）
collection = client.get_or_create_collection(name="cyber_law_collection")

# 4. 将文本块转化为向量并存入数据库
print("正在将数据向量化并存入数据库...")
print("（注：首次运行会自动下载默认的 Embedding 模型，这取决于网速，请耐心等待几分钟）")

# 准备存放数据的列表
documents_list = []
metadatas_list = []
ids_list = []

for i, chunk in enumerate(chunks):
    documents_list.append(chunk.page_content)
    # 给每一块数据打上元数据标签，方便以后溯源
    metadatas_list.append({"source": "《中华人民共和国网络安全法》"}) 
    ids_list.append(f"law_chunk_{i}")

# 批量写入数据库
collection.add(
    documents=documents_list,
    metadatas=metadatas_list,
    ids=ids_list
)

print("\n🎉 太棒了！《网络安全法》数据已成功向量化并永久存入本地数据库！")