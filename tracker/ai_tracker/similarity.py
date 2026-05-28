"""
代码行相似度计算引擎。
支持：精确匹配、归一化匹配、编辑距离、token 级相似度。
零外部依赖。
"""

import re
from functools import lru_cache
from typing import List, Optional, Tuple


# ── 归一化 ──────────────────────────────────────────────

@lru_cache(maxsize=4096)
def normalize_line(line: str) -> str:
    """
    归一化一行代码，消除无意义差异：
    - 去除首尾空白
    - 统一引号
    - 压缩连续空白为单个空格
    - 去除行尾注释（可选，保留代码语义）
    """
    s = line.strip()
    # 统一引号
    s = s.replace("'", '"')
    # 压缩空白（但保留字符串内的空白）
    # 简单处理：压缩所有连续空白
    s = re.sub(r'\s+', ' ', s)
    return s


# ── Levenshtein 编辑距离 ────────────────────────────────

def levenshtein(s1: str, s2: str) -> int:
    """计算两个字符串的编辑距离（优化空间 O(min(m,n))）"""
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    prev = list(range(len(s2) + 1))
    curr = [0] * (len(s2) + 1)

    for i, c1 in enumerate(s1, 1):
        curr[0] = i
        for j, c2 in enumerate(s2, 1):
            cost = 0 if c1 == c2 else 1
            curr[j] = min(
                curr[j - 1] + 1,       # 插入
                prev[j] + 1,            # 删除
                prev[j - 1] + cost,     # 替换
            )
        prev, curr = curr, prev

    return prev[len(s2)]


# ── Token 级相似度 ──────────────────────────────────────

_TOKEN_PATTERN = re.compile(r'[a-zA-Z_]\w*|[^\s\w]|\d+')


def tokenize(code: str) -> List[str]:
    """将代码行拆分为 token 列表"""
    return _TOKEN_PATTERN.findall(code)


def token_similarity(tokens1: List[str], tokens2: List[str]) -> float:
    """基于 token 的 Jaccard 相似度"""
    if not tokens1 and not tokens2:
        return 1.0
    if not tokens1 or not tokens2:
        return 0.0

    set1 = set(tokens1)
    set2 = set(tokens2)
    intersection = set1 & set2
    union = set1 | set2
    return len(intersection) / len(union) if union else 0.0


# ── 综合相似度 ──────────────────────────────────────────

def line_similarity(line1: str, line2: str) -> float:
    """
    计算两行代码的综合相似度 (0.0 ~ 1.0)。
    综合考虑：精确匹配 → 归一化匹配 → 编辑距离 → token 相似度。
    """
    # 快速路径：完全一致
    if line1 == line2:
        return 1.0

    # 归一化后比较
    n1 = normalize_line(line1)
    n2 = normalize_line(line2)

    if n1 == n2:
        return 0.99

    if not n1 and not n2:
        return 1.0
    if not n1 or not n2:
        return 0.0

    # 编辑距离相似度
    max_len = max(len(n1), len(n2))
    if max_len == 0:
        return 1.0
    edit_sim = 1.0 - (levenshtein(n1, n2) / max_len)

    # Token 相似度
    tok1 = tokenize(n1)
    tok2 = tokenize(n2)
    tok_sim = token_similarity(tok1, tok2)

    # 综合：短行更依赖编辑距离，长行更依赖 token 相似度
    if max_len < 40:
        return edit_sim * 0.7 + tok_sim * 0.3
    else:
        return edit_sim * 0.4 + tok_sim * 0.6


# ── 最佳匹配查找 ────────────────────────────────────────

def find_best_match(
    target: str,
    candidates: List[Tuple[str, str]],  # [(content, event_id), ...]
    threshold: float = 0.3,
) -> Optional[Tuple[str, str, float]]:
    """
    在候选列表中找到与 target 最相似的行。
    返回 (content, event_id, similarity) 或 None。
    """
    if not candidates:
        return None

    best_score = 0.0
    best_match = None

    for content, event_id in candidates:
        # 快速排除：长度差异过大
        max_len = max(len(target), len(content), 1)
        len_ratio = min(len(target), len(content)) / max_len
        if len_ratio < 0.2:
            continue

        score = line_similarity(target, content)
        if score > best_score:
            best_score = score
            best_match = (content, event_id, score)

    if best_match and best_match[2] >= threshold:
        return best_match

    return None


def find_block_match(
    target_lines: List[str],
    candidate_lines: List[str],
    min_block_size: int = 3,
) -> Tuple[float, int]:
    """
    在目标和候选之间寻找最长公共子序列（行级），用于块级匹配。
    返回 (匹配率，匹配行数)。
    """
    if not target_lines or not candidate_lines:
        return 0.0, 0

    m, n = len(target_lines), len(candidate_lines)

    # 预计算相似度矩阵，避免内层循环重复调用 line_similarity
    sim_matrix = [
        [line_similarity(target_lines[i], candidate_lines[j]) for j in range(n)]
        for i in range(m)
    ]

    # LCS with O(n) space
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if sim_matrix[i - 1][j - 1] > 0.8:
                curr[j] = prev[j - 1] + 1
            else:
                curr[j] = max(prev[j], curr[j - 1])
        prev, curr = curr, [0] * (n + 1)

    lcs_length = prev[n]
    match_rate = lcs_length / max(m, 1)

    return match_rate, lcs_length
