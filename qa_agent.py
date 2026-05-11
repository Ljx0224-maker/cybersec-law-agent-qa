# 接收用户问题，先用大模型提取关键词去查图谱，再用问题去查向量库，接着用 BGE 模型对向量库结果进行重排序（Rerank），最后将所有线索喂给大模型生成答案
import os
from dotenv import load_dotenv
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
import re
from langchain_community.vectorstores import FAISS
from neo4j import GraphDatabase
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.prompts import PromptTemplate
from sentence_transformers import CrossEncoder

load_dotenv()
ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

print("正在唤醒GraphRAG+Reranker智能问答Agent...")

embeddings = OpenAIEmbeddings(model="embedding-3", openai_api_key=ZHIPU_API_KEY, openai_api_base="https://open.bigmodel.cn/api/paas/v4/")
llm = ChatOpenAI(temperature=0.1, model="glm-4", openai_api_key=ZHIPU_API_KEY, openai_api_base="https://open.bigmodel.cn/api/paas/v4/")

vector_db = FAISS.load_local("./faiss_db", embeddings, allow_dangerous_deserialization=True)
neo4j_driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
reranker_model = CrossEncoder('BAAI/bge-reranker-base')

def extract_keywords(query):
    prompt = PromptTemplate(
        input_variables=["query"],
        template="""你是一个专业的法律词汇提取器。请从用户的提问中提取出核心的【法律专有名词】或【主客体名称】，用于知识图谱检索。
【提取规则】
1. 必须保留完整的法律概念，严禁过度切分！例如：将“网络关键设备”作为一个整体提取。
2. 如果用户提到了某部具体的法律（如《数据安全法》），请务必将其作为关键词提取出来。
3. 不要提取太泛的词（如“国家”、“规定”、“什么”、“特殊”、“要求”）。
4. 只返回词语本身，用逗号隔开。

用户提问：{query}"""
    )
    chain = prompt | llm
    result = chain.invoke({"query": query})
    return [k.strip() for k in result.content.replace('，', ',').split(',') if k.strip()]

def extract_keywords_from_doc(doc_text):
    """专门用于从长文档中提取涉嫌违规的业务实体，用于后续检索"""
    prompt = PromptTemplate(
        input_variables=["doc_text"],
        template="""你是一个专业的法律合规审查员。请阅读以下待审查的文件内容，提取出其中可能涉及网络安全和数据合规风险的【核心业务动作】或【数据处理对象】。
【提取规则】
1. 重点提取如：身份注册、生物识别、地理位置、数据出境、网络日志、安全事件等敏感词汇。
2. 不要提取泛泛的废话（如“公司”、“管理”、“规范”、“用户”）。
3. 只返回词语本身，用逗号隔开，最多提取 8 个最核心的词。

待审查文件内容：
{doc_text}"""
    )
    chain = prompt | llm
    result = chain.invoke({"doc_text": doc_text})
    # 清洗并返回列表
    return [k.strip() for k in result.content.replace('，', ',').split(',') if k.strip()]

def search_graph_db(keywords):
    graph_results = []
    with neo4j_driver.session() as session:
        for kw in keywords:
            cypher_query = """
            MATCH (n)-[r]->(m)
            WHERE n.name CONTAINS $keyword OR m.name CONTAINS $keyword
            RETURN n.name AS source, 
                   type(r) AS relation, 
                   m.name AS target
            LIMIT 5
            """
            result = session.run(cypher_query, keyword=kw)
            for record in result:
                chain_str = f"[{record['source']}] --({record['relation']})--> [{record['target']}]"
                graph_results.append(chain_str)
    return list(set(graph_results))

def search_vector_with_reranker(query, keywords):
    vip_texts = [] 
    
    # 精准条文号狙击
    match = re.search(r'第[一二三四五六七八九十百千万]+条', query)
    if match:
        target_article = match.group(0) 
        for doc in vector_db.docstore._dict.values():
            if target_article in doc.page_content and doc.page_content not in vip_texts:
                vip_texts.append(doc.page_content)
                print(f"[VIP通道] 触发精确制导法条: {target_article}")
                
    # 实体字典强制挂载
    # 提取用户想问的核心词
    target_terms = [k for k in keywords] if keywords else []
    
    # 把网络安全法的五个核心名词直接写死，只要问题里有，就拉入检测范围
    for w in ["网络", "网络安全", "网络运营者", "网络数据", "个人信息"]:
        if w in query and w not in target_terms:
            target_terms.append(w)

    for doc in vector_db.docstore._dict.values():
        content = doc.page_content
        # 只要是定义类法条（包含 附则 / 名词解释 / 含义 / 第七十八条 任意一个特征）
        if any(marker in content for marker in ["名词解释", "本法下列用语的含义", "第七十八条", "含义"]):
            for term in target_terms:
                # 只要该法条同时包含了用户问的核心名词，并且有“是指”这个定义的标志
                if term in content and "是指" in content:
                    if content not in vip_texts:
                        vip_texts.append(content)
                        print(f"[VIP通道] 实体拦截成功！强行保送【{term}】相关的定义法条。")

    # --- 传统 FAISS 向量粗排补充 ---
    docs = vector_db.similarity_search(query, k=40)
    raw_texts = []
    for doc in docs:
        if doc.page_content not in vip_texts:
            raw_texts.append(doc.page_content)
            
    # --- BGE 交叉精排（只对普通文本进行打分和内卷） ---
    scored_texts = []
    if raw_texts:
        sentence_pairs = [[query, text] for text in raw_texts]
        scores = reranker_model.predict(sentence_pairs)
        scored_texts = list(zip(raw_texts, scores))
        scored_texts.sort(key=lambda x: x[1], reverse=True)
    
    normal_top_10 = [item[0] for item in scored_texts[:10]]
    
    # VIP 文本强制排在最前面
    final_results = vip_texts + normal_top_10
    
    return final_results[:15]
def generate_final_answer(query, vector_context, graph_context):
    prompt_template = """
    你是一个权威的国家法律合规 AI 顾问。
    请你严格基于检索到的信息来综合回答用户的咨询。
    
    回答规则：
    1. 【隐藏系统痕迹】（最高红线！）绝对严禁在回答中出现“根据提供的【参考法条原文】”、“结合【图谱逻辑链路】”、“根据已知信息”等暴露系统底层检索机制的字眼。请表现得像一个真实、专业的人类律师，直接用自然流畅的语言给出解答。
    2. 【引经据典】回答必须明确说明真实的法律出处（例如：“根据《网络安全法》第X条规定”），用具体的法律名称替代干瘪的“参考资料”。
    3. 【定义优先红线】如果用户询问某个概念的定义，且资料中包含该词的法定“名词解释”（含“是指...”字样），你必须在回答的开头，一字不差地引用该法定解释的原文。
    4. 【复合问题必答】如果用户的提问包含多个部分（例如：“什么是XXX？它包含哪些？”），你必须在给出严谨的法定定义后，继续分点回答用户的后续补充问题！严禁只回答定义而忽略后续问题。
    5. 【禁止主观臆断】在解答延伸问题时，只能依据给定的资料进行分类归纳，如果不确定或资料未提及具体细节，请如实说明“现有法律法规中暂未对具体名单进行穷尽列举”。
    
    【图谱逻辑链路】:
    {graph_context}
    
    【参考法条原文】:
    {vector_context}
    
    【用户问题】:
    {query}
    
    请直接给出你的专业解答：
    """
    prompt = PromptTemplate(input_variables=["graph_context", "vector_context", "query"], template=prompt_template)
    chain = prompt | llm
    
    str_graph = "\n".join(graph_context) if graph_context else "未检索到相关逻辑链"
    str_vector = "\n\n".join(vector_context) if vector_context else "未检索到相关法条"
    
    response = chain.invoke({"graph_context": str_graph, "vector_context": str_vector, "query": query})
    return response.content

if __name__ == "__main__":
    print("\nAgent 已就绪！多法域双路知识引擎连接成功。")
    
    # 测试
    query_text = "国家对关键信息基础设施的运营者在数据存储方面有什么要求？"
    print(f"\n提问: {query_text}")
    
    print("1. 提取关键词...")
    keywords = extract_keywords(query_text)
    print(f"   -> 提取到: {keywords}")
    
    print("2. 检索图谱数据库...")
    graph_info = search_graph_db(keywords)
    
    print("3. 启动双阶段向量检索 (FAISS粗排 + Reranker精排)...")
    vector_info = search_vector_with_reranker(query_text, keywords)
    
    print("4. 融合生成解答...\n")
    final_answer = generate_final_answer(query_text, vector_info, graph_info)
    
    print("【AI 法律顾问解答】:\n" + final_answer)
    neo4j_driver.close()