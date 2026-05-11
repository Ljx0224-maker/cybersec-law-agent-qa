#实现真正的 GraphRAG（图谱 + 向量 双路检索增强），彻底消灭通用大模型在法律领域的“幻觉”
from langchain_chroma import Chroma  # 修复了旧版警告
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate

# ==========================================
# 1. 核心配置信息 (⚠️请替换)
# ==========================================
ZHIPU_API_KEY = "727d6d03b7f7476083c38633fd768d88.W1QqCdjuBks6sZMk"
NEO4J_URI = "neo4j+ssc://29c2d4cd.databases.neo4j.io" 
NEO4J_USERNAME = "29c2d4cd"
NEO4J_PASSWORD = "wTIrS4zu4MV5HpUBAYx4H6ELrWZN084-3EChCWuJ7yM"

print("🤖 正在唤醒 [完全体 - 调优版] 网络安全法智能问答 Agent...")

embeddings = OpenAIEmbeddings(
    model="embedding-3",
    openai_api_key=ZHIPU_API_KEY,
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
)

llm = ChatOpenAI(
    temperature=0.1, 
    model="glm-4",
    openai_api_key=ZHIPU_API_KEY,
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/"
)

vector_db = Chroma(
    persist_directory="./chroma_db_v2",
    embedding_function=embeddings,
    collection_name="cyber_law_collection_v2"
)

neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))

# ==========================================
# 3. 定义 Agent 的核心工作流
# ==========================================

def extract_keywords(query):
    """任务 1：升级版关键词提取，严禁提取泛泛的词"""
    prompt = PromptTemplate(
        input_variables=["query"],
        template="请从以下法律咨询问题中，提取出最核心的2-3个实体名词（例如特定的主体、客体、行为）。严禁提取“时间”、“规定”、“要求”等宽泛词汇。只需返回词语本身，用逗号隔开。\n问题：{query}"
    )
    chain = prompt | llm
    result = chain.invoke({"query": query})
    
    content = result.content.replace('，', ',')
    keywords = [k.strip() for k in content.split(',') if k.strip()]
    return keywords

def search_graph_db(keywords):
    graph_context = []
    with neo4j_driver.session() as session:
        for keyword in keywords:
            cypher_query = """
            MATCH (h)-[r]->(t)
            WHERE h.name CONTAINS $keyword OR t.name CONTAINS $keyword
            RETURN h.name AS head, type(r) AS relation, t.name AS tail
            LIMIT 5
            """
            results = session.run(cypher_query, keyword=keyword)
            for record in results:
                path = f"({record['head']}) -> [{record['relation']}] -> ({record['tail']})"
                if path not in graph_context:
                    graph_context.append(path)
    return graph_context

def search_vector_db(query):
    """任务 3：扩大检索视野，从 k=2 提升到 k=5"""
    docs = vector_db.similarity_search(query, k=5) 
    return [doc.page_content for doc in docs]

def generate_final_answer(query, vector_context, graph_context):
    prompt_template = """
    你是一个权威的《网络安全法》AI 法律顾问。
    请你严格基于下面提供的【参考法条原文】和【图谱逻辑链路】来回答用户的咨询。
    
    规则：
    1. 优先使用图谱逻辑链路梳理结构。
    2. 引用法条原文中的具体细节（如时间、罚款金额等）。
    3. 如果参考信息中没有答案，明确回答“根据已知信息无法作答”，严禁凭空捏造。
    
    【图谱逻辑链路】:
    {graph_context}
    
    【参考法条原文】:
    {vector_context}
    
    【用户问题】:
    {query}
    
    请给出你的专业解答：
    """
    prompt = PromptTemplate(input_variables=["graph_context", "vector_context", "query"], template=prompt_template)
    chain = prompt | llm
    
    str_graph = "\n".join(graph_context) if graph_context else "未检索到相关逻辑链 (注: 可能是该法条尚未录入图谱)"
    str_vector = "\n".join(vector_context) if vector_context else "未检索到相关法条"
    
    print("\n" + "="*40)
    print("🔍 [内部推理过程] 检视引擎获取的上下文：")
    print(f"-> 提取的图谱逻辑:\n{str_graph}")
    print(f"-> 提取的法条片段:\n{str_vector}")
    print("="*40 + "\n")
    
    response = chain.invoke({"graph_context": str_graph, "vector_context": str_vector, "query": query})
    return response.content

if __name__ == "__main__":
    print("✅ Agent 已就绪！双路知识引擎连接成功。")
    
    query_text = "网络产品若不符合相关国家标准的强制会怎样处罚？"
    print(f"\n👤 提问: {query_text}")
    
    print("⚙️ 提取关键词...")
    keywords = extract_keywords(query_text)
    print(f"   -> 提取到: {keywords}")
    
    print("⚙️ 并发检索双库...")
    graph_info = search_graph_db(keywords)
    vector_info = search_vector_db(query_text)
    
    print("⚙️ 融合生成解答...\n")
    final_answer = generate_final_answer(query_text, vector_info, graph_info)
    
    print("👩‍⚖️ 【AI 法律顾问解答】:\n" + final_answer)
    neo4j_driver.close()