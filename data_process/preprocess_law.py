# 数据预处理，自动化清洗与结构化：将网上下载的、排版杂乱的法律纯文本（txt），按照正则表达式精准切分成“【法律名 - 章节名】第X条 内容”的标准化格式
import re
import os

def parse_law_dynamic(file_path):
    """
    通用法律解析器：自动提取法律名称、动态追踪章节、精确切分法条
    """
    law_name = os.path.basename(file_path).replace('.txt', '')
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    results = []
    current_chapter = "" 
    current_article_num = ""
    current_article_content = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # 1. 识别章节头
        if re.match(r'^第[一二三四五六七八九十百千万]+[章编]', line):
            current_chapter = line
            continue
            
        # 2. 识别法条头
        match_article = re.match(r'^(第[一二三四五六七八九十百千万]+条)\s*(.*)', line)
        if match_article:
            if current_article_num:
                # 动态判断前缀：如果有章节就拼接，没有就只写法律名
                prefix = f"【{law_name} - {current_chapter}】" if current_chapter else f"【{law_name}】"
                final_text = f"{prefix} {current_article_num} {current_article_content.strip()}"
                results.append(final_text)
            
            current_article_num = match_article.group(1)
            current_article_content = match_article.group(2)
        else:
            # 3. 拼接多行内容
            if current_article_num:
                current_article_content += " " + line
                
    # 收尾
    if current_article_num:
        prefix = f"【{law_name} - {current_chapter}】" if current_chapter else f"【{law_name}】"
        final_text = f"{prefix} {current_article_num} {current_article_content.strip()}"
        results.append(final_text)
        
    return law_name, results