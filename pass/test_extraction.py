#编写大语言模型抽取脚本,知识图谱抽取测试
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
import json

print("--- 开启知识图谱实体抽取测试 ---")

# 1. 配置大语言模型 (接入智谱 GLM-4)
# ⚠️ 请将下面这行替换成你刚才申请的真实 API Key
ZHIPU_API_KEY = "727d6d03b7f7476083c38633fd768d88.W1QqCdjuBks6sZMk" 

print("正在初始化大语言模型...")
llm = ChatOpenAI(
    temperature=0.1, # 温度设为极低，保证法律抽取的严谨性和格式稳定
    model="glm-4",
    openai_api_key=ZHIPU_API_KEY,
    openai_api_base="https://open.bigmodel.cn/api/paas/v4/" # 智谱的接口地址
)

# 2. 定义我们在沙盘推演时设计好的 Schema 和 Prompt
prompt_template = """
你是一个顶级的法律知识图谱构建专家。你的任务是从《网络安全法》的文本中抽取实体和关系，构建三元组。

【实体类型定义 (Entity Types)】
1. 法条节点: 如"第二十一条"
2. 主体: 法律约束的对象，如"网络运营者"、"国家网信部门"
3. 行为/义务: 法律要求执行或禁止的动作，如"留存网络日志"、"制定安全管理制度"
4. 客体/属性: 行为作用的对象或附加属性，如"不少于六个月"、"个人信息"
5. 法律责任: 违法的后果，如"罚款"、"责令改正"

【关系类型定义 (Relation Types)】
1. 约束 (法条节点 -> 主体)
2. 须履行 (主体 -> 行为/义务)
3. 须禁止 (主体 -> 行为/义务)
4. 作用于 (行为/义务 -> 客体/属性)
5. 违反导致 (行为/义务 -> 法律责任)

【待抽取文本】
{text}

【输出要求】
请严格按照以下 JSON 数组格式输出，不要输出任何额外的解释性文字，不要使用 Markdown 代码块标记（如 ```json），直接输出 JSON 本身：
[
  {{"head": "实体1名称", "head_type": "实体1类型", "relation": "关系名称", "tail": "实体2名称", "tail_type": "实体2类型"}}
]
"""

prompt = PromptTemplate(
    input_variables=["text"],
    template=prompt_template
)

# 3. 选取一段真实的法条进行测试
sample_law_text = "第二十一条 国家实行网络安全等级保护制度。网络运营者应当采取监测、记录网络运行状态、网络安全事件的技术措施，并按照规定留存相关的网络日志不少于六个月。"
print(f"\n【输入文本】: {sample_law_text}")

# 4. 执行抽取任务
print("\n正在呼叫大模型进行深度逻辑抽取（请稍候...）")
chain = prompt | llm
response = chain.invoke({"text": sample_law_text})

# 5. 打印并解析结果
print("\n=== 大模型输出的原始结果 ===")
print(response.content)

try:
    # 尝试将结果解析为 Python 的字典列表，验证其格式是否正确
    triples = json.loads(response.content)
    print("\n✅ 解析成功！一共抽取到了", len(triples), "个三元组。")
    print("这代表大模型完全理解了我们的 Schema，并且输出了完美的结构化数据！")
except json.JSONDecodeError:
    print("\n❌ 解析失败：大模型输出的格式不符合严格的 JSON 标准。")

print("\n--- 测试完毕 ---")