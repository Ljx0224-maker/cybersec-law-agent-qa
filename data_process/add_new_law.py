# 将新的法律文件切分，并同步注入到 FAISS 向量库和 Neo4j 知识图谱中
import os
import json
import time
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain.prompts import PromptTemplate
from neo4j import GraphDatabase
from data_process.preprocess_law import parse_law_dynamic
from dotenv import load_dotenv

load_dotenv()
# 配置智谱接口和Neo4j数据库、FATSS向量库
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")
FAISS_DIR = "./faiss_db"

def process_new_law(file_path):
    print(f"\n开始处理新法律文件: {file_path}")
    law_name, chunks = parse_law_dynamic(file_path)
    print(f"解析完成：[{law_name}]，共提取 {len(chunks)} 条结构化法条。")

    # 模块一：增量更新 FAISS 向量库
    print("\n--- 1. 正在更新 FAISS 向量库 ---")
    embeddings = OpenAIEmbeddings(model="embedding-3", openai_api_key=ZHIPU_API_KEY, openai_api_base="https://open.bigmodel.cn/api/paas/v4/")
    documents = [Document(page_content=chunk) for chunk in chunks]
    
    batch_size = 50 # 智谱单次最高64，设为50比较安全：设定批处理大小，防止一次性发送太多请求导致 API 报错
    
    if os.path.exists(FAISS_DIR):
        print("检测到已有向量库，执行分批增量挂载...")
        db = FAISS.load_local(FAISS_DIR, embeddings, allow_dangerous_deserialization=True)
        # 循环分批追加
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            db.add_documents(batch_docs)
            print(f"   -> 成功追加第 {i+1} 到 {min(i+batch_size, len(documents))} 条向量数据")
    else:
        print("未检测到已有向量库，分批创建全新库...")
        # 第一批用来初始化库
        db = FAISS.from_documents(documents[:batch_size], embeddings)
        print(f"   -> 成功初始化并写入前 {min(batch_size, len(documents))} 条向量数据")
        # 剩下的循环追加
        for i in range(batch_size, len(documents), batch_size):
            batch_docs = documents[i : i + batch_size]
            db.add_documents(batch_docs)
            print(f"   -> 成功追加第 {i+1} 到 {min(i+batch_size, len(documents))} 条向量数据")
            
    db.save_local(FAISS_DIR)
    print("FAISS 向量库更新成功！")

    # 模块二：增量更新 Neo4j 知识图谱
    print("\n--- 2. 正在更新 Neo4j 知识图谱 ---")
    neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
    llm = ChatOpenAI(temperature=0.1, model="glm-4", openai_api_key=ZHIPU_API_KEY, openai_api_base="https://open.bigmodel.cn/api/paas/v4/")
    
    prompt_template = """你是一个顶级的法律知识图谱构建专家。请从以下法条文本中抽取实体和关系。

    【核心抽取规则】
    1. 传入的文本开头包含法律名称和法条编号。你抽取的中心法条节点（head），名称必须严格遵守格式："《{law_name}》第X条"。例如："《网络安全法》第一条"。绝对不能只写"第一条"！
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

    for i, text in enumerate(chunks):
        print(f"正在抽取 [{law_name}] 第 {i+1}/{len(chunks)} 条关系网络...")
        try:
            response = chain.invoke({"law_name": law_name, "text": text})
            content = response.content.replace('```json', '').replace('```', '').strip()
            triples = json.loads(content)
            write_to_neo4j(triples)
            time.sleep(1.5) 
        except Exception as e:
            print(f"第 {i+1} 条处理出错: {e}")

    neo4j_driver.close()
    print(f"\n法律 [{law_name}] 成功并入系统全局大脑！")

if __name__ == "__main__":
    # 指向我们刚刚排版好的完整文本
    target_file = "./data/中华人民共和国网络安全法.txt" 
    process_new_law(target_file)