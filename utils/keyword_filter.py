#coding=utf-8
"""
本地敏感词过滤服务
使用简单的字符串匹配，后续可升级为 Aho-Corasick 算法
"""

import json
import os
import logging
import re
from typing import Dict, List, Tuple, Optional

_keyword_data = None
_keyword_patterns = {}


def load_keywords(force_reload: bool = False) -> Dict:
    """加载敏感词库到内存"""
    global _keyword_data, _keyword_patterns
    
    if _keyword_data and not force_reload:
        return _keyword_data
    
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', 'sensitive_keywords.json')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            _keyword_data = json.load(f)
        
        _keyword_patterns = {}
        for category, data in _keyword_data.get('categories', {}).items():
            words = data.get('words', [])
            if words:
                pattern = '|'.join(re.escape(w) for w in words)
                _keyword_patterns[category] = {
                    'pattern': re.compile(pattern, re.IGNORECASE),
                    'severity': data.get('severity', 'medium'),
                    'words': set(w.lower() for w in words)
                }
        
        logging.info(f"敏感词库加载成功: {len(_keyword_patterns)} 个类别")
        return _keyword_data
        
    except Exception as e:
        logging.error(f"加载敏感词库失败: {e}")
        _keyword_data = {'categories': {}}
        return _keyword_data


def check_text(text: str) -> Dict:
    """
    检查文本中是否包含敏感词
    
    返回:
        {
            'safe': bool,
            'matched_keywords': [{'word': str, 'category': str, 'severity': str}],
            'highest_severity': str or None
        }
    """
    if not text:
        return {'safe': True, 'matched_keywords': [], 'highest_severity': None}
    
    load_keywords()
    
    text_lower = text.lower()
    text_normalized = normalize_text(text)
    
    matched = []
    severity_order = {'high': 3, 'medium': 2, 'low': 1}
    highest_severity = None
    highest_severity_level = 0
    
    for category, data in _keyword_patterns.items():
        pattern = data['pattern']
        severity = data['severity']
        
        for match in pattern.finditer(text_normalized):
            word = match.group()
            matched.append({
                'word': word,
                'category': category,
                'severity': severity
            })
            
            level = severity_order.get(severity, 0)
            if level > highest_severity_level:
                highest_severity_level = level
                highest_severity = severity
    
    matched = list({m['word']: m for m in matched}.values())
    
    return {
        'safe': len(matched) == 0,
        'matched_keywords': matched,
        'highest_severity': highest_severity
    }


def normalize_text(text: str) -> str:
    """
    规范化文本，处理常见的规避手段
    - 移除空格、特殊字符
    - 转换全角为半角
    - 处理谐音字
    """
    text = text.lower()
    
    full_to_half = str.maketrans(
        '　！＂＃＄％＆＇（）＊＋，－．／０１２３４５６７８９：；＜＝＞？＠ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ［＼］＾＿｀ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ｛｜｝～',
        ' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'
    )
    text = text.translate(full_to_half)
    
    text = re.sub(r'[\s\u200b\u200c\u200d\ufeff]', '', text)
    
    replacements = {
        '0': 'o', 'о': 'o',
        '1': 'i', 'l': 'i',
        '3': 'e',
        '4': 'a',
        '5': 's',
        '8': 'b',
        '@': 'a',
        '$': 's',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


def filter_text(text: str, replacement: str = '*') -> Tuple[str, List[str]]:
    """
    过滤文本中的敏感词，替换为指定字符
    
    返回:
        (filtered_text, list_of_replaced_words)
    """
    if not text:
        return text, []
    
    load_keywords()
    
    replaced_words = []
    result = text
    
    for category, data in _keyword_patterns.items():
        pattern = data['pattern']
        
        def replace_match(match):
            word = match.group()
            replaced_words.append(word)
            return replacement * len(word)
        
        result = pattern.sub(replace_match, result)
    
    return result, replaced_words


def get_severity_for_word(word: str) -> Optional[str]:
    """获取特定词的严重程度"""
    load_keywords()
    
    word_lower = word.lower()
    for category, data in _keyword_patterns.items():
        if word_lower in data['words']:
            return data['severity']
    return None


def add_keyword(word: str, category: str, severity: str = 'medium') -> bool:
    """动态添加敏感词（仅内存中，不持久化）"""
    global _keyword_patterns
    
    load_keywords()
    
    if category not in _keyword_patterns:
        _keyword_patterns[category] = {
            'pattern': None,
            'severity': severity,
            'words': set()
        }
    
    _keyword_patterns[category]['words'].add(word.lower())
    
    words = list(_keyword_patterns[category]['words'])
    pattern = '|'.join(re.escape(w) for w in words)
    _keyword_patterns[category]['pattern'] = re.compile(pattern, re.IGNORECASE)
    
    return True


if __name__ == '__main__':
    load_keywords()
    
    test_cases = [
        "这是一个正常的商品描述",
        "你这个傻逼",
        "TMD真的太气人了",
        "加微信领取优惠",
        "这个商品质量很好，推荐购买"
    ]
    
    for text in test_cases:
        result = check_text(text)
        print(f"文本: {text}")
        print(f"  安全: {result['safe']}")
        if not result['safe']:
            print(f"  匹配词: {result['matched_keywords']}")
            print(f"  最高严重程度: {result['highest_severity']}")
        print()
