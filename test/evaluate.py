import pandas as pd
import time
import os

# 导入原有的检索函数和模型
from qa_agent import (
    vector_db, 
    reranker_model, 
    extract_keywords, 
    search_graph_db, 
    search_vector_with_reranker
)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

def check_hit(retrieved_texts, target_str):
    """
    检查目标法条是否命中。支持多个目标法条逗号分隔。
    """
    targets = [t.strip() for t in str(target_str).replace('、', ',').split(',') if t.strip()]
    combined_text = " ".join(retrieved_texts)
    
    for t in targets:
        if t in combined_text:
            return True
    return False

def run_evaluation():
    print("正在加载带【标准答案要点】的增强测试集...")
    dataset_file = "test_dataset.csv"  # 切换至全新的增强测试集
    try:
        df = pd.read_csv(dataset_file)
        data = df.to_dict(orient="records")
        print(f"成功加载 {len(data)} 条测试数据！开始自动化消融实验评估与生成对齐分析...\n")
    except Exception as e:
        print(f"读取测试集失败，请检查文件名。错误信息: {e}")
        return

    categories = ["名词解释", "责任认定", "复杂推理"]
    
    hits = {
        "FAISS": {c: 0 for c in categories},
        "FAISS+BGE": {c: 0 for c in categories},
        "System": {c: 0 for c in categories}
    }
    totals = {c: 0 for c in categories}
    results_for_generation_eval = []

    for index, item in enumerate(tqdm(data, desc="🚀 正在评估")):
        q_type = str(item.get("问题类型", ""))
        query = str(item.get("测试问题", ""))
        target = str(item.get("目标法条", ""))
        standard_answer = str(item.get("标准答案要点", ""))
        
        matched_type = None
        for c in categories:
            if c in q_type:
                matched_type = c
                break
        if not matched_type:
            continue

        totals[matched_type] += 1

        # 1. 纯 FAISS 向量检索
        docs_a = vector_db.similarity_search(query, k=10)
        texts_a = [doc.page_content for doc in docs_a]
        if check_hit(texts_a, target):
            hits["FAISS"][matched_type] += 1

        # 2. FAISS + BGE (精排)
        docs_b = vector_db.similarity_search(query, k=40)
        raw_texts_b = [doc.page_content for doc in docs_b]
        if raw_texts_b:
            sentence_pairs = [[query, text] for text in raw_texts_b]
            scores = reranker_model.predict(sentence_pairs)
            scored_texts = list(zip(raw_texts_b, scores))
            scored_texts.sort(key=lambda x: x[1], reverse=True)
            texts_b = [item[0] for item in scored_texts[:10]]
        else:
            texts_b = []
            
        if check_hit(texts_b, target):
            hits["FAISS+BGE"][matched_type] += 1
            
        # 3. 本系统: 图谱召回 + 旁路拦截 + 向量精排
        try:
            keywords = extract_keywords(query)
            graph_info = search_graph_db(keywords)
            vector_info = search_vector_with_reranker(query, keywords)
            system_texts = graph_info + vector_info
            
            system_hit = check_hit(system_texts, target)
            if system_hit:
                hits["System"][matched_type] += 1
                
            # 记录本系统最终的上下文信息，供生成质量定性评估
            results_for_generation_eval.append({
                "question": query,
                "type": matched_type,
                "standard_answer_points": standard_answer,
                "system_context": " ".join(system_texts)[:200] + "..." # 截断展示
            })
        except Exception as e:
            pass

    print("\n\n" + "="*70)
    print("一、系统检索架构消融实验结果 (Hit@10 召回率) ✨")
    print("="*70)
    
    total_q = sum(totals.values())
    print(f"总计参与测试题数: {total_q} 题")
    for c in categories:
        print(f"  - {c}类: {totals[c]} 题")
    print("-" * 70)
    
    headers = ["检索架构设计", "名词解释类", "责任认定类", "复杂推理类", "综合平均召回率"]
    print(f"| {headers[0]:<35} | {headers[1]:<10} | {headers[2]:<10} | {headers[3]:<10} | {headers[4]:<12} |")
    print(f"|{'-'*37}|{'-'*15}|{'-'*15}|{'-'*15}|{'-'*18}|")
    
    methods = [("FAISS", "FAISS"), ("FAISS+BGE精排", "FAISS+BGE"), ("本系统(混合检索+旁路召回)", "System")]
    
    for display_name, dict_key in methods:
        row_str = f"| {display_name:<35} |"
        total_hits = 0
        for c in categories:
            t = totals[c]
            h = hits[dict_key][c]
            total_hits += h
            pct = f"{(h / t * 100):.1f}%" if t > 0 else "0.0%"
            row_str += f" {pct:^13} |"
        avg_pct = f"{(total_hits / total_q * 100):.1f}%" if total_q > 0 else "0.0%"
        row_str += f" {avg_pct:^16} |"
        print(row_str)
        
    print("\n\n" + "="*70)
    print("二、生成质量定性评估依据 (标准答案要点核对) ✨")
    print("="*70)
    complex_samples = [r for r in results_for_generation_eval if r['type'] == '复杂推理']
    if complex_samples:
        sample = complex_samples[0]
        print(f"\n【测试问题（案例）】: {sample['question']}")
        print(f"\n【标准答案要点（评分指标）】:\n{sample['standard_answer_points']}")
        print("\n-> 核对大模型最终生成的解答是否覆盖上述所有主体对应的处罚要点，从而证明该系统的推理价值。")

if __name__ == "__main__":
    run_evaluation()