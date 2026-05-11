#测试检索的脚本,检索功能测试
import chromadb

print("--- 开始测试法律知识库检索 ---")

# 1. 连接我们刚才建好的本地数据库
print("正在连接数据库...")
client = chromadb.PersistentClient(path="./chroma_db")

# 获取我们存入数据的集合（表）
# 注意这里用的是 get_collection，因为我们确定它已经存在了
collection = client.get_collection(name="cyber_law_collection")

# 2. 模拟用户提出一个法律咨询问题
# 你可以把这里换成任何你想问的关于网络安全法的问题
query_text = "网络运营者如果不履行安全保护义务，会被怎么处罚？"
print(f"\n【用户提问】: {query_text}")

# 3. 在数据库中进行相似度检索 (Semantic Search)
print("\n正在知识库中检索最相关的法条...")
results = collection.query(
    query_texts=[query_text],
    n_results=3  # 核心参数：告诉数据库返回最相关的 3 个文本块 (Top-K)
)

# 4. 打印检索结果
print("\n=== 检索到的相关法条片段 ===")
# results['documents'][0] 包含了检索出来的所有文本块内容
for i, doc in enumerate(results['documents'][0]):
    print(f"\n[片段 {i+1}]")
    print(doc)
    # 打印我们存入的元数据（出处）
    metadata = results['metadatas'][0][i]
    print(f"-> 来源: {metadata['source']}")

print("\n--- 测试完毕 ---")