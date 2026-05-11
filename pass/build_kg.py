#创建终极图谱构建脚本
import chromadb
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from neo4j import GraphDatabase
import json
import time

# --- 1. 核心配置信息 (⚠️请替换为你自己的真实信息) ---
ZHIPU_API_KEY = "727d6d03b7f7476083c38633fd768d88.W1QqCdjuBks6sZMk"
NEO4J_URI = "neo4j+ssc://29c2d4cd.databases.neo4j.io"        # 例如: neo4j+s://29c2d4cd.databases.neo4j.io
NEO4J_USERNAME = "29c2d4cd"           # 默认用户名通常是 neo4j，如果不是请修改
NEO4J_PASSWORD = "wTIrS4zu4MV5HpUBAYx4H6ELrWZN084-3EChCWuJ7yM"    # 刚才让你保存的那个密码

print("--- 启动知识图谱自动化构建引擎 ---")

# --- 2. 初始化连接 ---
print("正在连接本地 ChromaDB 向量数据库...")
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_collection(name="cyber_law_collection")

print("正在连接云端 Neo4j 图数据库...")
# 建立与 Neo4j 的官方驱动连接
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

print("正在初始化智谱大语言模型...")
llm = ChatOpenAI(
    temperature=0.1,
    model="glm-4",
    openai_api_key=ZHIPU_API_KEY,
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
)

# 沿用我们之前测试成功的完美 Prompt
prompt_template = """
你是一个顶级的法律知识图谱构建专家。你的任务是从《网络安全法》的文本中抽取实体和关系，构建三元组。

【实体类型】: 法条节点, 主体, 行为/义务, 客体/属性, 法律责任
【关系类型】: 约束, 须履行, 须禁止, 作用于, 违反导致

【待抽取文本】
{text}

请严格输出JSON数组，不要包含其他文字：
[
  {{"head": "实体1", "head_type": "类型", "relation": "关系", "tail": "实体2", "tail_type": "类型"}}
]
"""
prompt = PromptTemplate(input_variables=["text"], template=prompt_template)
chain = prompt | llm

# --- 3. 定义 Neo4j 写入函数 ---
def write_to_neo4j(triples):
    with neo4j_driver.session() as session:
        for triple in triples:
            head = triple.get("head")
            head_type = triple.get("head_type")
            relation = triple.get("relation")
            tail = triple.get("tail")
            tail_type = triple.get("tail_type")

            if not all([head, relation, tail]):
                continue

            # Cypher 图谱查询语言：MERGE 语句能确保“如果实体存在就不重复创建，直接连线”
            query = f"""
            MERGE (h:Entity {{name: $head}})
            ON CREATE SET h.type = $head_type
            MERGE (t:Entity {{name: $tail}})
            ON CREATE SET t.type = $tail_type
            MERGE (h)-[r:`{relation}`]->(t)
            """
            session.run(query, head=head, head_type=head_type, tail=tail, tail_type=tail_type)

# --- 4. 批量处理主逻辑 ---
print("\n--- 开始批量抽取并存入图数据库 ---")
# 测试阶段：我们只从向量库里拿出前 3 个切片进行处理
all_docs = collection.get(limit=3)
chunks = all_docs['documents']

for i, text in enumerate(chunks):
    print(f"\n正在处理第 {i+1}/{len(chunks)} 个文本块...")
    try:
        # 1. 呼叫大模型抽取
        response = chain.invoke({"text": text})
        
        # 2. 清理并解析 JSON
        content = response.content.replace('```json', '').replace('```', '').strip()
        triples = json.loads(content)
        
        # 3. 写入 Neo4j
        write_to_neo4j(triples)
        print(f"✅ 成功抽取并写入 {len(triples)} 条关系链路！")
        
        # 稍微停顿一下，给大模型 API 喘口气的时间
        time.sleep(2)
        
    except Exception as e:
        print(f"❌ 处理第 {i+1} 个文本块时出错: {e}")

# 关闭数据库连接
neo4j_driver.close()
print("\n🎉 知识图谱初步构建完成！请前往 Neo4j 云端控制台查看属于你的星辰大海！")