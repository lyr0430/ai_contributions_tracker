"""终端报告 + JSON 报告生成，跨平台 ANSI 颜色支持"""

import json
import sys
from pathlib import Path
from typing import Optional

from .models import AnalysisResult


# ── 跨平台 ANSI 颜色 ────────────────────────────────────

def _supports_color() -> bool:
    """检测终端是否支持 ANSI 颜色"""
    # Windows 10+ Terminal / PowerShell / VS Code 终端都支持
    if sys.platform == "win32":
        try:
            import os
            os.system("")  # 启用 ANSI on Windows
            return True
        except Exception:
            return False
    if not hasattr(sys.stdout, "isatty"):
        return False
    return sys.stdout.isatty()


_COLOR = _supports_color()

def _c(text: str, code: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOR else text

def bold(t): return _c(t, "1")
def dim(t): return _c(t, "2")
def green(t): return _c(t, "32")
def yellow(t): return _c(t, "33")
def red(t): return _c(t, "31")
def cyan(t): return _c(t, "36")
def magenta(t): return _c(t, "35")


# ── 终端报告 ────────────────────────────────────────────

def print_report(result: AnalysisResult, repo_root: Path = None) -> None:
    """打印彩色终端报告"""
    w = 60  # 报告宽度

    print()
    print(bold(cyan("=" * w)))
    print(bold(cyan("  AI 代码贡献报告")))
    print(bold(cyan("=" * w)))
    print()

    # 概览
    print(f"  分析文件数：{len(result.files)}")
    print(f"  Push 总行数：{result.total_push_lines}")
    print(f"  AI 事件数：{result.ai_events_count}")
    print()

    # 核心指标
    print(bold("  ┌─────────────────────────────────────────────┐"))

    gen = result.generation_rate * 100
    ret = result.retention_rate * 100
    net = result.net_contribution * 100

    print(bold(f"  │  AI 生成率  : {_rate_color(gen, 5)}"))
    print(dim( "  │  (AI 写的行 / session 总变更行)"))
    print(bold(f"  │  AI 存活率  : {_rate_color(ret, 5)}"))
    print(dim( "  │  (留在 push 中的 AI 行 / AI 写的总数)"))
    print(bold(f"  │  AI 净贡献  : {_rate_color(net, 5)}"))
    print(dim( "  │  (最终 push 中可归因 AI 行 / 总行数)"))
    print(bold("  └─────────────────────────────────────────────┘"))
    print()

    # AI 原始生成量
    print(bold("  AI 原始生成量（含后续被修改/删除的）:"))
    print(f"    行数：{result.ai_generated_lines}  字符数：{result.ai_generated_chars}")
    print()
    print()

    # 分解
    total = result.total_push_lines or 1
    print(bold("  明细:"))
    print(f"    {green('■')} 纯 AI (未修改)          : {result.ai_pure_total:>5}  ({result.ai_pure_total/total*100:5.1f}%)")
    print(f"    {yellow('■')} AI 原作 (已修改)        : {result.ai_modified_total:>5}  ({result.ai_modified_total/total*100:5.1f}%)")
    print(f"    {magenta('■')} 混合贡献               : {result.mixed_total:>5}  ({result.mixed_total/total*100:5.1f}%)")
    print(f"    {dim('■')} 人工编写               : {result.human_total:>5}  ({result.human_total/total*100:5.1f}%)")
    print(f"    {red('×')} AI 生成 (已删除)        : {result.deleted_ai_total:>5}  (未进入 push)")
    print()

    # 每文件详情
    if result.files:
        print(bold("  文件明细:"))
        print()

        # 表头
        fp_width = min(40, max(len(f.file_path) for f in result.files) + 2)
        header = f"    {'文件':<{fp_width}} {'AI%':>6} {'纯 AI':>5} {'修改':>5} {'混合':>5} {'人工':>5} {'已删':>5}"
        print(bold(header))
        print("    " + "─" * (fp_width + 34))

        for fa in result.files:
            fp_display = fa.file_path
            if len(fp_display) > fp_width:
                fp_display = "..." + fp_display[-(fp_width - 3):]

            ai_pct = fa.ai_contribution_ratio * 100
            print(
                f"    {fp_display:<{fp_width}} "
                f"{_rate_color(ai_pct, 3):>6} "
                f"{fa.ai_pure_lines:>5} "
                f"{fa.ai_modified_lines:>5} "
                f"{fa.mixed_lines:>5} "
                f"{fa.human_lines:>5} "
                f"{_deleted_count(fa.file_path, result):>5}"
            )

    # 被删除的 AI 代码（只显示前 10 条）
    if result.deleted_ai:
        print()
        print(bold(f"  已删除的 AI 代码 (共 {result.deleted_ai_total} 行):"))
        for da in result.deleted_ai[:10]:
            print(f"    {red('×')} {dim(da.file_path)}: {da.content[:60]}")
        if result.deleted_ai_total > 10:
            print(f"    {dim(f'... 还有 {result.deleted_ai_total - 10} 行')}")

    print()
    print(bold(cyan("=" * w)))
    print()


def _rate_color(value: float, width: int = 5) -> str:
    """根据百分比值返回彩色字符串"""
    s = f"{value:>{width}.1f}%"
    if value > 70:
        return green(s)
    elif value > 30:
        return yellow(s)
    elif value > 0:
        return red(s)
    return dim(s)


def _deleted_count(file_path: str, result: AnalysisResult) -> int:
    return sum(1 for d in result.deleted_ai if d.file_path == file_path)


# ── JSON 报告 ───────────────────────────────────────────

def save_json_report(result: AnalysisResult, output_path: Path) -> None:
    """保存 JSON 格式报告"""
    report = {
        "summary": {
            "total_push_lines": result.total_push_lines,
            "ai_events_count": result.ai_events_count,
            "ai_events_total_lines": result.ai_events_total_lines,
            "generation_rate": round(result.generation_rate, 4),
            "retention_rate": round(result.retention_rate, 4),
            "net_contribution": round(result.net_contribution, 4),
            "ai_generated_lines": result.ai_generated_lines,
            "ai_generated_chars": result.ai_generated_chars,
            "breakdown": {
                "ai_pure": result.ai_pure_total,
                "ai_modified": result.ai_modified_total,
                "mixed": result.mixed_total,
                "human": result.human_total,
                "deleted_ai": result.deleted_ai_total,
            },
            "chars": {
                "ai_pure": result.ai_pure_chars,
                "ai_modified": result.ai_modified_chars,
                "mixed": result.mixed_chars,
                "human": result.human_chars,
                "total": result.total_chars,
            },
        },
        "files": [
            {
                "path": fa.file_path,
                "total_lines": fa.total_lines,
                "ai_contribution_ratio": round(fa.ai_contribution_ratio, 4),
                "ai_pure": fa.ai_pure_lines,
                "ai_modified": fa.ai_modified_lines,
                "mixed": fa.mixed_lines,
                "human": fa.human_lines,
                "line_details": [
                    {
                        "line": la.line_number,
                        "source": la.source,
                        "ai_ratio": round(la.ai_ratio, 4),
                        "similarity": round(la.similarity_score, 4),
                    }
                    for la in fa.line_details
                ],
            }
            for fa in result.files
        ],
        "deleted_ai_lines": [
            {
                "file": da.file_path,
                "content": da.content,
                "event_id": da.event_id,
            }
            for da in result.deleted_ai
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# ── Markdown 报告（用于 PR 评论等） ─────────────────────

def generate_markdown_report(result: AnalysisResult) -> str:
    """生成 Markdown 格式报告"""
    total = result.total_push_lines or 1
    lines = [
        "## AI 代码贡献报告\n",
        "| 指标 | 值 |",
        "|------|-----|",
        f"| AI 生成率 | **{result.generation_rate*100:.1f}%** |",
        f"| AI 存活率 | **{result.retention_rate*100:.1f}%** |",
        f"| AI 净贡献 | **{result.net_contribution*100:.1f}%** |",
        f"| 分析文件数 | {len(result.files)} |",
        f"| Push 总行数 | {result.total_push_lines} |",
        "",
        "### 明细\n",
        f"- 纯 AI 行：**{result.ai_pure_total}** ({result.ai_pure_total/total*100:.1f}%)",
        f"- AI 原作 (已修改): **{result.ai_modified_total}** ({result.ai_modified_total/total*100:.1f}%)",
        f"- 混合贡献：**{result.mixed_total}** ({result.mixed_total/total*100:.1f}%)",
        f"- 人工编写：**{result.human_total}** ({result.human_total/total*100:.1f}%)",
        f"- AI 生成 (已删除): **{result.deleted_ai_total}** (未进入 push)",
        "",
    ]

    if result.files:
        lines.append("### 文件明细\n")
        lines.append("| 文件 | AI% | 纯 AI | 修改 | 混合 | 人工 |")
        lines.append("|------|-----|------|------|------|------|")
        for fa in result.files:
            lines.append(
                f"| `{fa.file_path}` "
                f"| {fa.ai_contribution_ratio*100:.1f}% "
                f"| {fa.ai_pure_lines} "
                f"| {fa.ai_modified_lines} "
                f"| {fa.mixed_lines} "
                f"| {fa.human_lines} |"
            )

    return "\n".join(lines)
