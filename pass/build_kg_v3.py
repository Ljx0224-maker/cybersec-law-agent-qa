#Neo4j图谱构建
import json
import time
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from neo4j import GraphDatabase
from preprocess_law import parse_cybersecurity_law

# ⚠️ 请替换为你自己的真实信息
ZHIPU_API_KEY = "727d6d03b7f7476083c38633fd768d88.W1QqCdjuBks6sZMk"
NEO4J_URI = "neo4j+ssc://29c2d4cd.databases.neo4j.io"        # 例如: neo4j+s://29c2d4cd.databases.neo4j.io
NEO4J_USERNAME = "29c2d4cd"           # 默认用户名通常是 neo4j，如果不是请修改
NEO4J_PASSWORD = "wTIrS4zu4MV5HpUBAYx4H6ELrWZN084-3EChCWuJ7yM"    # 刚才让你保存的那个密码

print("--- 启动 V3 终极版知识图谱构建引擎 (元数据锚定版) ---")

chunks = parse_cybersecurity_law("./data/cybersecurity_law.txt")
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

print("正在清空旧版图谱数据，准备写入全新星系图...")
with neo4j_driver.session() as session:
    session.run("MATCH (n) DETACH DELETE n")

llm = ChatOpenAI(
    temperature=0.1, 
    model="glm-4", 
    openai_api_key=ZHIPU_API_KEY, 
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
)

prompt_template = """你是一个顶级的法律知识图谱构建专家。请从以下带有元数据的法条文本中抽取实体和关系，构建三元组。

【核心抽取规则】
1. 传入的文本开头通常包含法条编号。你必须抽取出一个 head 为该法条编号（如"第二十三条"），head_type 为 "法条节点" 的中心节点。
2. 将该法条中涉及的主体、行为/义务、客体等，与这个"法条节点"建立联系。
3. 允许的关系类型: 包含, 约束, 须履行, 作用于, 违反导致。
4. 严格输出JSON数组，不要包含其他文字。

【待抽取文本】
{text}
"""
prompt = PromptTemplate(input_variables=["text"], template=prompt_template)
chain = prompt | llm

def write_to_neo4j(triples):
    with neo4j_driver.session() as session:
        for triple in triples:
            head = triple.get("head")
            head_type = triple.get("head_type", "未知")
            relation = triple.get("relation")
            tail = triple.get("tail")
            tail_type = triple.get("tail_type", "未知")
            
            if not all([head, relation, tail]):
                continue
                
            query = """
            MERGE (h:Entity {name: $head}) 
            ON CREATE SET h.type = $head_type 
            MERGE (t:Entity {name: $tail}) 
            ON CREATE SET t.type = $tail_type 
            MERGE (h)-[r:`""" + relation + """`]->(t)
            """
            session.run(query, head=head, head_type=head_type, tail=tail, tail_type=tail_type)

print("\n--- 开始批量抽取并存入图数据库 ---")
for i, text in enumerate(chunks):
    print(f"正在处理第 {i+1} 条结构化数据...")
    try:
        response = chain.invoke({"text": text})
        content = response.content.replace('```json', '').replace('```', '').strip()
        triples = json.loads(content)
        write_to_neo4j(triples)
        print(f"✅ 成功抽取并写入 {len(triples)} 条关系！")
        time.sleep(2)
    except Exception as e:
        print(f"❌ 处理出错: {e}")

neo4j_driver.close()
print("\n🎉 V3版星系知识图谱构建完成！")