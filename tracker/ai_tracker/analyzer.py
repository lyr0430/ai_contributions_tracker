"""
核心分析引擎：关联 AI 事件与 Git diff，计算每行的贡献归因。

工作流：
1. 获取即将 push 的变更（git diff upstream..HEAD）
2. 加载所有 AI 事件
3. 对每个变更文件，构建"AI 行池"
4. 对每个变更行，做模糊匹配归因
5. 统计"消失的 AI 代码"
"""

import re
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from .config import (
    THRESHOLD_AI_MODIFIED,
    THRESHOLD_AI_PURE,
    THRESHOLD_MIXED,
)
from .event_store import load_events, load_snapshot
from .models import (
    AnalysisResult,
    DeletedAIContribution,
    Event,
    FileAttribution,
    LineAttribution,
)
from .similarity import find_best_match, line_similarity


# ── Git 操作 ────────────────────────────────────────────

def _run_git(args: List[str], cwd: Path) -> Tuple[str, int]:
    """执行 git 命令，返回 (stdout, returncode)"""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
        return result.stdout, result.returncode
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return "", 1


def get_upstream_ref(repo_root: Path) -> Optional[str]:
    """获取上游分支引用（如 origin/main）"""
    stdout, rc = _run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"],
        repo_root,
    )
    if rc == 0:
        return stdout.strip()
    return None


def _should_exclude(file_path: str) -> bool:
    """判断文件是否应该排除在分析之外"""
    # 排除 .gitignore 中的文件
    if file_path.startswith(".gitignore"):
        return True
    # 排除 Python 缓存
    if "__pycache__" in file_path or file_path.endswith(".pyc"):
        return True
    # 排除 ai_tracker 自身（工具代码）
    if file_path.startswith("ai_tracker/"):
        return True
    # 排除测试文件
    if file_path.startswith("tests/"):
        return True
    # 排除 .agentsroom 内部目录
    if file_path.startswith(".agentsroom/"):
        return True
    # 排除 .claude 配置
    if file_path.startswith(".claude/"):
        return True
    # 排除临时脚本
    if file_path.endswith("test-install.sh"):
        return True
    return False


def get_changed_files(repo_root: Path, base_ref: str) -> List[str]:
    """获取 base_ref..HEAD 之间变更的文件列表（已排除不相关文件）"""
    # 使用 -z 避免中文文件名转义问题
    stdout, rc = _run_git(
        ["diff", "--name-only", "-z", f"{base_ref}..HEAD"],
        repo_root,
    )
    if rc != 0:
        return []
    files = [f.strip() for f in stdout.split('\0') if f.strip()]
    return [f for f in files if not _should_exclude(f)]


def get_file_content_at_head(repo_root: Path, file_path: str) -> Optional[List[str]]:
    """获取 HEAD 中某文件的完整内容（行列表）"""
    stdout, rc = _run_git(["show", f"HEAD:{file_path}"], repo_root)
    if rc != 0:
        return None
    return stdout.splitlines()


def get_diff_lines(
    repo_root: Path, base_ref: str, file_path: str
) -> Dict[int, str]:
    """
    获取某文件在 base_ref..HEAD 之间的变更行。
    返回 {行号 (HEAD 中的): 行内容}，只包含新增和修改的行。
    如果 base_ref 不存在或 diff 为空，返回 HEAD 完整内容（用于已提交文件）。
    """
    stdout, rc = _run_git(
        ["diff", f"{base_ref}..HEAD", "--unified=0", "--", file_path],
        repo_root,
    )
    if rc != 0 or not stdout.strip():
        # 没有 diff（已提交或新文件），返回 HEAD 完整内容（带行号）
        head_lines = get_file_content_at_head(repo_root, file_path)
        if head_lines is None:
            return {}
        return {i + 1: line for i, line in enumerate(head_lines)}

    changed_lines: Dict[int, str] = {}
    current_line = 0

    for line in stdout.splitlines():
        # 解析 @@ -a,b +c,d @@ 行
        hunk_match = re.match(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@', line)
        if hunk_match:
            current_line = int(hunk_match.group(1))
            continue

        if line.startswith('+') and not line.startswith('+++'):
            changed_lines[current_line] = line[1:]
            current_line += 1
        elif line.startswith('-') and not line.startswith('---'):
            pass  # 删除的行不计入
        else:
            current_line += 1

    return changed_lines


def get_new_branch_files(repo_root: Path) -> List[str]:
    """当没有 upstream 时，获取所有已提交的文件（已排除不相关文件）"""
    stdout, rc = _run_git(["ls-tree", "-r", "--name-only", "HEAD"], repo_root)
    if rc != 0:
        return []
    files = [f.strip() for f in stdout.splitlines() if f.strip()]
    return [f for f in files if not _should_exclude(f)]


# ── 分析核心 ────────────────────────────────────────────

def analyze(
    repo_root: Path,
    base_ref: Optional[str] = None,
) -> AnalysisResult:
    """
    主分析入口。
    base_ref: 比较基准，如 origin/main。None 时自动检测。
    """
    result = AnalysisResult()

    # Step 1: 确定基准
    if base_ref is None:
        base_ref = get_upstream_ref(repo_root)

    is_new_branch = base_ref is None
    if is_new_branch:
        # 新分支，没有 upstream，对比空树
        base_ref = "4b825dc642cb6eb9a060e54bf899d15f3f9381e0"  # git empty tree hash

    # Step 2: 获取变更文件
    changed_files = get_changed_files(repo_root, base_ref)
    if not changed_files and is_new_branch:
        changed_files = get_new_branch_files(repo_root)

    # Step 3: 加载所有 AI 事件
    all_events = load_events(repo_root)
    result.ai_events_count = len(all_events)

    # 没有 AI 事件，直接返回空报告
    if not all_events:
        return result

    # 按文件索引 AI 事件
    events_by_file: Dict[str, List[Event]] = {}
    for evt in all_events:
        events_by_file.setdefault(evt.file_path, []).append(evt)

    # 分析所有有 AI 事件的文件（不依赖 git diff）
    files_with_ai = set(events_by_file.keys())
    # 如果没有 git 变更，直接分析所有 AI 文件（已提交场景）
    if not changed_files:
        changed_files = [f for f in files_with_ai if not _should_exclude(f)]
    else:
        changed_files = [f for f in changed_files if f in files_with_ai]

    # Step 4: 逐文件分析
    ai_pool_global: Dict[str, List[Tuple[str, str]]] = {}  # file -> [(content, event_id)]
    snapshot_pool_global: Dict[str, List[str]] = {}         # file -> [lines from snapshots]

    for file_path in changed_files:
        # 收集该文件的 AI 行池
        ai_pool = _build_ai_pool(file_path, events_by_file, repo_root)
        ai_pool_global[file_path] = ai_pool

        # 收集快照中的行（用于统计"消失"的代码）
        snap_lines = _collect_snapshot_lines(file_path, events_by_file)
        snapshot_pool_global[file_path] = snap_lines

        # 获取最终内容和变更行
        final_lines = get_file_content_at_head(repo_root, file_path)
        if final_lines is None:
            continue

        changed = get_diff_lines(repo_root, base_ref, file_path)

        # 归因分析
        fa = _attribute_file(file_path, final_lines, changed, ai_pool)
        result.files.append(fa)
        result.total_push_lines += fa.total_lines

    # Step 5: 统计"消失的 AI 代码"
    result.deleted_ai = _find_deleted_ai(
        ai_pool_global, snapshot_pool_global, result.files, repo_root, events_by_file,
    )

    # Step 6: 统计 AI 事件总行数
    for evt in all_events:
        result.ai_events_total_lines += len(evt.diff.added)

    return result


def _build_ai_pool(
    file_path: str,
    events_by_file: Dict[str, List[Event]],
    repo_root: Path,
) -> List[Tuple[str, str]]:
    """
    为一个文件构建"AI 行池"：所有 AI 曾经写入过的内容。
    返回 [(行内容，事件 ID), ...]
    """
    pool: List[Tuple[str, str]] = []
    events = events_by_file.get(file_path, [])

    for evt in events:
        # 从事件 diff 中获取 AI 写入的行
        for _line_no, content in evt.diff.added.items():
            pool.append((content, evt.id))

        # 也从快照中提取（更可靠的完整状态）
        if evt.snapshot_path:
            snap_lines = load_snapshot(evt.snapshot_path)
            if snap_lines:
                for line in snap_lines:
                    pool.append((line, evt.id))

    # 去重
    seen = set()
    unique_pool = []
    for content, eid in pool:
        key = content.strip()
        if key and key not in seen:
            seen.add(key)
            unique_pool.append((content, eid))

    return unique_pool


def _collect_snapshot_lines(
    file_path: str,
    events_by_file: Dict[str, List[Event]],
) -> List[str]:
    """从所有快照中收集该文件的行（用于检测被删除的 AI 代码）"""
    all_lines: List[str] = []
    events = events_by_file.get(file_path, [])
    for evt in events:
        if evt.snapshot_path:
            snap = load_snapshot(evt.snapshot_path)
            if snap:
                all_lines.extend(snap)
    return all_lines


def _attribute_file(
    file_path: str,
    final_lines: List[str],
    changed_lines: Dict[int, str],
    ai_pool: List[Tuple[str, str]],
) -> FileAttribution:
    """对一个文件的所有变更行进行归因"""
    fa = FileAttribution(file_path=file_path)
    fa.total_lines = len(changed_lines) if changed_lines else len(final_lines)

    if not changed_lines:
        # 整个文件都是新的（新分支场景）
        changed_lines = {i + 1: line for i, line in enumerate(final_lines)}
        fa.total_lines = len(final_lines)

    # 第一轮：逐行归因
    for line_no, content in changed_lines.items():
        attribution = _attribute_line(content, ai_pool)

        la = LineAttribution(
            line_number=line_no,
            content=content,
            source=attribution["source"],
            ai_ratio=attribution["ai_ratio"],
            matched_event_id=attribution.get("event_id"),
            similarity_score=attribution.get("score", 0.0),
        )

        fa.line_details.append(la)

    # 第二轮：上下文修正 — 如果文件大部分是 AI 写的，剩余未匹配行也归为 AI
    if ai_pool:
        ai_count = sum(1 for la in fa.line_details if la.source in ("ai_pure", "ai_modified"))
        mixed_count = sum(1 for la in fa.line_details if la.source == "mixed")
        total = len(fa.line_details)
        if total > 0 and (ai_count + mixed_count) / total >= 0.5:
            # 超过 50% 是 AI 写的，剩余 human 行降级为 ai_modified
            for la in fa.line_details:
                if la.source == "human":
                    # 再试一次更宽松的匹配
                    match = find_best_match(la.content, ai_pool, threshold=0.15)
                    if match:
                        _, event_id, score = match
                        la.source = "ai_modified"
                        la.ai_ratio = max(score, 0.5)
                        la.matched_event_id = event_id
                        la.similarity_score = score

    # 统计行数和字符数
    for la in fa.line_details:
        char_count = len(la.content)
        fa.total_chars += char_count
        fa.ai_weighted_sum += la.ai_ratio

        if la.source == "ai_pure":
            fa.ai_pure_lines += 1
            fa.ai_pure_chars += char_count
        elif la.source == "ai_modified":
            fa.ai_modified_lines += 1
            fa.ai_modified_chars += char_count
        elif la.source == "mixed":
            fa.mixed_lines += 1
            fa.mixed_chars += char_count
        else:
            fa.human_lines += 1
            fa.human_chars += char_count

    return fa


def _attribute_line(
    content: str,
    ai_pool: List[Tuple[str, str]],
) -> dict:
    """对单行进行归因，返回 {source, ai_ratio, event_id, score}"""
    if not ai_pool:
        return {"source": "human", "ai_ratio": 0.0}

    match = find_best_match(content, ai_pool, threshold=THRESHOLD_MIXED)

    if match is None:
        return {"source": "human", "ai_ratio": 0.0}

    _, event_id, score = match

    if score >= THRESHOLD_AI_PURE:
        return {"source": "ai_pure", "ai_ratio": 1.0, "event_id": event_id, "score": score}
    elif score >= THRESHOLD_AI_MODIFIED:
        # AI 为主体，人工微调
        ai_ratio = score  # 相似度直接作为贡献比例
        return {"source": "ai_modified", "ai_ratio": ai_ratio, "event_id": event_id, "score": score}
    elif score >= THRESHOLD_MIXED:
        # 混合贡献
        ai_ratio = score * 0.5
        return {"source": "mixed", "ai_ratio": ai_ratio, "event_id": event_id, "score": score}
    else:
        return {"source": "human", "ai_ratio": 0.0}


def _find_deleted_ai(
    ai_pool_global: Dict[str, List[Tuple[str, str]]],
    snapshot_pool_global: Dict[str, List[str]],
    file_attributions: List[FileAttribution],
    repo_root: Path,
    events_by_file: Dict[str, List[Event]],
) -> List[DeletedAIContribution]:
    """
    找出 AI 写过但最终没出现在 push 里的代码。
    通过对比 AI 快照行 vs 最终文件内容。
    """
    deleted: List[DeletedAIContribution] = []

    for file_path, snap_lines in snapshot_pool_global.items():
        # 获取最终内容
        final_lines_set: Set[str] = set()
        for fa in file_attributions:
            if fa.file_path == file_path:
                for la in fa.line_details:
                    final_lines_set.add(la.content.strip())
                break

        # 如果文件不在 push 的变更列表中，获取 HEAD 内容
        if not final_lines_set:
            head_content = get_file_content_at_head(repo_root, file_path)
            if head_content:
                final_lines_set = {line.strip() for line in head_content}

        # 对比：AI 写过的行中，哪些不在最终内容里
        for snap_line in snap_lines:
            stripped = snap_line.strip()
            if not stripped or len(stripped) < 4:
                continue  # 忽略太短的行（如空行、单括号）

            # 精确匹配检查
            if stripped in final_lines_set:
                continue

            # 模糊匹配检查：是否在最终内容中有相似的行
            found_similar = False
            for final_line in final_lines_set:
                if line_similarity(stripped, final_line) > 0.8:
                    found_similar = True
                    break

            if not found_similar:
                # 找到所属事件
                events = events_by_file.get(file_path, [])
                event_id = events[0].id if events else "unknown"
                for evt in events:
                    for _ln, added_content in evt.diff.added.items():
                        if added_content.strip() == stripped:
                            event_id = evt.id
                            break

                deleted.append(DeletedAIContribution(
                    file_path=file_path,
                    content=stripped,
                    event_id=event_id,
                ))

    # 限制数量，避免噪声（比如格式化前的空格差异产生大量误报）
    # 只保留前 500 条
    return deleted[:500]
