# 处理数据补丁：精准定位到某一部法律的某一条，单独重新抽取并打入图谱，无需重新跑整部法律，防止模型抽取图谱时偶尔出错或中断
import json
import os
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from neo4j import GraphDatabase
from data_process.preprocess_law import parse_law_dynamic
from dotenv import load_dotenv

load_dotenv()
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# 1、在这里填入你刚才正在跑的法律 txt 文件路径
target_file = "./data/互联网上网服务营业场所管理条例.txt"  # <--- 请务必修改这里！
law_name, chunks = parse_law_dynamic(target_file)

# 2、锁定目标法条
# 你想补第 13 条，它在程序列表里的索引就是 12 (因为索引从0开始)
target_article_num = 21
target_index = target_article_num - 1 

# 提取出那唯一的一条文本
target_text = chunks[target_index]

neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
llm = ChatOpenAI(temperature=0.1, model="glm-4", openai_api_key=ZHIPU_API_KEY, openai_api_base="https://open.bigmodel.cn/api/paas/v4/")

prompt_template = """你是一个顶级的法律知识图谱构建专家。请从以下法条文本中抽取实体和关系。

【核心抽取规则】
1. 传入的文本开头包含法律名称和法条编号。你抽取的中心法条节点（head），名称必须严格遵守格式："《{law_name}》第X条"。例如："《数据安全法》第一条"。绝对不能只写"第一条"！
2. 将法条中涉及的主体、行为/义务、客体等，与这个带法律名称的法条节点建立联系。
3. 允许的关系类型: 包含, 约束, 须履行, 作用于, 违反导致。
4. 严格输出JSON数组，不要包含其他文字。格式如：[{{ "head": "《{law_name}》第一条", "head_type": "法条", "relation": "约束", "tail": "网络运营者", "tail_type": "主体" }}]

【待抽取文本】
{text}
"""
prompt = PromptTemplate(input_variables=["law_name", "text"], template=prompt_template)
chain = prompt | llm

def write_to_neo4j(triples):
    with neo4j_driver.session() as session:
        for triple in triples:
            head, head_type = triple.get("head"), triple.get("head_type", "未知")
            relation, tail, tail_type = triple.get("relation"), triple.get("tail"), triple.get("tail_type", "未知")
            if not all([head, relation, tail]): continue
            query = """
            MERGE (h:Entity {name: $head}) 
            ON CREATE SET h.type = $head_type 
            MERGE (t:Entity {name: $tail}) 
            ON CREATE SET t.type = $tail_type 
            MERGE (h)-[r:`""" + relation + """`]->(t)
            """
            session.run(query, head=head, head_type=head_type, tail=tail, tail_type=tail_type)

print(f"\n正在为 [{law_name}] 执行【第 {target_article_num} 条】单点修补手术...")
print(f"将要处理的原文片段: {target_text[:40]}...") # 打印前40个字让你确认一下没抓错

try:
    response = chain.invoke({"law_name": law_name, "text": target_text})
    content = response.content.replace('```json', '').replace('```', '').strip()
    triples = json.loads(content)
    write_to_neo4j(triples)
    print(f"第 {target_article_num} 条的节点和关系已完美并入知识图谱。")
except Exception as e:
    print(f"处理出错: {e}")

neo4j_driver.close()