# 基于智能体的网络安全法律 GraphRAG 问答系统

> **核心技术**：深度融合 LLM Agent + Neo4j 知识图谱 + FAISS 向量检索。通过“双路并发”与“确定性旁路”机制，将垂直领域问答召回率提升至 94.7%，成功解决法条张冠李戴的幻觉问题。

[![Python 3.9+](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![GLM-4](https://img.shields.io/badge/LLM-GLM--4-red.svg)](https://bigmodel.cn/)
[![Neo4j](https://img.shields.io/badge/GraphDB-Neo4j-008CC1.svg)](https://neo4j.com/)
[![FAISS](https://img.shields.io/badge/VectorDB-FAISS-yellow.svg)](https://github.com/facebookresearch/faiss)
[![BGE-Reranker](https://img.shields.io/badge/Rerank-BGE--Reranker-green.svg)](https://huggingface.co/BAAI/bge-reranker-v2-m3)

---

## 核心架构：双路并发召回

系统不仅关注语义相似度，更强调法律逻辑的严密性。其核心流程如下：

1. **意图解析**：Agent 提取用户 Query 中的法律实体与行为。
2. **向量路径 (FAISS)**：捕捉语义关联，召回 Top-40 潜在相关切片。
3. **图谱路径 (Neo4j)**：通过 Cypher 语句提取法条间的拓扑关系（主体、违规行为、法律责任）。
4. **确定性旁路 (Innovation)**：针对“名词解释”等强定义需求，通过正则与锚点实现 100% 准确提取。
5. **精排 (BGE-Reranker)**：交叉编码计算 Query-Doc 细粒度交互分数，阻断幻觉源头。

---

## 技术亮点与难点突破

### 1. 抑制大模型幻觉：确定性旁路算法

* **痛点**：传统 RAG 在检索简短的法律定义（如“什么是网络运营者”）时，常因语义稀疏被长文本噪声掩盖。
* **解决方案**：自研旁路拦截机制，检测到定义类查询后，直接从知识图谱中根据“是指”等谓词逻辑提取法条原文，权重设为无穷大，强制 LLM 逐字引用。

### 2. 解决“高频词挤兑”：GraphRAG 架构

* **痛点**：在《网络安全法》中，“网络”等高频词会导致向量检索结果大量同质化，掩盖核心条款。
* **解决方案**：利用 Neo4j 维系“法条-章节-实体”的逻辑链条，实现从“语义匹配”向“逻辑推导”的跨越。

### 3. 数据工程：元数据锚定切片

* **策略**：摒弃粗暴的固定长度切分，采用基于正则表达式的动态状态机，将法律文本按“条”进行物理切割。
* **成果**：每一段召回内容均隐式注入【法律名-章节-法条号】元数据，实现“白盒化”溯源。

---

## 模块化功能实现

* **语句问答交互和基于用户上传文档问答交互**：支持用户上传文档（TXT），Agent 自动解析风险锚点并对照底层法条，随后根据用户问题进行回答。
* **推理过程可视化**：前端 Streamlit 开发了专用推理面板，实时展示关键词提取结果、图谱逻辑链路与精排得分。
* **持久化**：采用 SQLite 管理会话，通过 UUID 与 SHA-256 哈希保障多用户会话隔离与数据安全。

已经部署上线，访问：https://cybersec-law-agent-app.streamlit.app/

## 最终效果展示：

**首页：**<img width="2199" height="1196" alt="image" src="https://github.com/user-attachments/assets/6acb8dfa-63dc-4046-a435-3cd9a2178a1f" />

**问答交互页（主要功能）：**<img width="2199" height="1182" alt="image" src="https://github.com/user-attachments/assets/b86ba78a-49de-499f-907a-a307802722e2" />

**系统管理员工作台界面：**<img width="2207" height="1189" alt="image" src="https://github.com/user-attachments/assets/c9ef21c7-c894-49af-9f27-f7842d72ad65" />

<img width="2191" height="1184" alt="image" src="https://github.com/user-attachments/assets/b4001fc0-2795-4920-899c-7e2929700d59" />







