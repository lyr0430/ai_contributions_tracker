"""
CLI 入口：
  python -m ai_tracker install         # 安装所有 hooks
  python -m ai_tracker pre-push        # 执行 push 分析（被 git hook 调用）
  python -m ai_tracker analyze         # 手动执行分析
  python -m ai_tracker hook            # 被 Claude Code hook 调用
"""

import argparse
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        prog="ai-tracker",
        description="Track AI code contribution rates",
    )
    sub = parser.add_subparsers(dest="command")

    # install
    p_install = sub.add_parser("install", help="Install git and Claude Code hooks")
    p_install.add_argument("--python", default=None, help="Python command to use in hooks")
    p_install.add_argument("--server", default=None, help="Server URL (e.g. http://localhost:8000)")

    # pre-push（被 git hook 自动调用）
    p_prepush = sub.add_parser("pre-push", help="Run pre-push analysis (called by git hook)")
    p_prepush.add_argument("--push", default=None, help="Push to server URL")
    p_prepush.add_argument("--project", default=None, help="Project name")

    # analyze（手动执行）
    p_analyze = sub.add_parser("analyze", help="Manually run contribution analysis")
    p_analyze.add_argument("--base", default=None, help="Base ref (e.g. origin/main)")
    p_analyze.add_argument("--json", default=None, help="Save JSON report to path")
    p_analyze.add_argument("--markdown", action="store_true", help="Output markdown report")
    p_analyze.add_argument("--push", default=None, help="Push to server URL (e.g. http://localhost:8000)")
    p_analyze.add_argument("--project", default=None, help="Project name (default: repo name)")

    # hook（被 Claude Code hook 调用）
    sub.add_parser("hook", help="Process Claude Code hook event (reads stdin)")

    # report（查询统计）
    p_report = sub.add_parser("report", help="Query contribution reports from server")
    p_report.add_argument("--server", required=True, help="Server URL (e.g. http://localhost:8000)")
    p_report.add_argument("--project", default=None, help="Filter by project name")
    p_report.add_argument("--author", default=None, help="Filter by author name")
    p_report.add_argument("--from", dest="from_date", default=None, help="From date (YYYY-MM-DD)")
    p_report.add_argument("--to", dest="to_date", default=None, help="To date (YYYY-MM-DD)")
    p_report.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.command == "install":
        _cmd_install(args)
    elif args.command == "pre-push":
        run_pre_push_analysis(server_url=args.push, project_name=args.project)
    elif args.command == "analyze":
        _cmd_analyze(args)
    elif args.command == "hook":
        from .hook_handler import handle_hook
        handle_hook()
    elif args.command == "report":
        _cmd_report(args)
    else:
        parser.print_help()


def _cmd_install(args):
    from .installer import install_all
    from .config import find_repo_root

    root = find_repo_root()
    install_all(repo_root=root, python_path=args.python, server_url=args.server)


def run_pre_push_analysis(server_url: str = None, project_name: str = None):
    """Pre-push hook 调用的分析入口 - 统一处理 AI 和手动修改"""
    from .config import init_paths, REPORT_FILE, DEFAULT_SERVER_URL
    from .analyzer import analyze, get_upstream_ref
    from .reporter import print_report, save_json_report, generate_markdown_report
    from .event_store import load_events

    server_url = server_url or DEFAULT_SERVER_URL

    try:
        from .config import find_repo_root
        repo_root = find_repo_root()
    except RuntimeError:
        print("[ai-tracker] Not in a git repository, skipping analysis.", file=sys.stderr)
        return 0

    init_paths(repo_root)

    # 读取 pre-push stdin 获取待推送的 commit 范围
    push_commits = _read_push_stdin(repo_root)

    # 分析
    base_ref = get_upstream_ref(repo_root)
    result = analyze(repo_root, base_ref=base_ref)

    # 输出报告
    print_report(result, repo_root)

    # 保存 JSON 报告
    report_path = REPORT_FILE or (repo_root / ".ai-contributions" / "report.json")
    save_json_report(result, report_path)
    print(f"  Report saved: {report_path}")

    # 读取 AI 事件
    ai_events = load_events(repo_root)
    ai_files = {e.file_path for e in ai_events}

    # Push to server（按 commit 分别推送，记录每个作者）
    _push_to_server(server_url, result, repo_root, project_name, ai_files, push_commits)

    return 0


def _cmd_analyze(args):
    from .config import init_paths, REPORT_FILE
    from .analyzer import analyze
    from .reporter import print_report, save_json_report, generate_markdown_report

    from .config import find_repo_root
    repo_root = find_repo_root()
    init_paths(repo_root)

    result = analyze(repo_root, base_ref=args.base)
    print_report(result, repo_root)

    if args.json:
        save_json_report(result, Path(args.json))
        print(f"  JSON report: {args.json}")

    if args.markdown:
        md = generate_markdown_report(result)
        print(md)

    # Push to server（默认使用内置地址）
    from .config import DEFAULT_SERVER_URL
    server_url = args.push or DEFAULT_SERVER_URL
    _push_to_server(server_url, result, repo_root, args.project)


def _read_push_stdin(repo_root: Path) -> list:
    """
    读取 git pre-push hook 通过 stdin 传入的 commit 范围。
    格式: local_ref local_sha remote_ref remote_sha
    返回待推送的 commit hash 列表。
    """
    import subprocess

    commits = []
    try:
        for line in sys.stdin:
            parts = line.strip().split()
            if len(parts) >= 2:
                local_sha = parts[1]
                # 获取从 remote 到 local 之间的所有 commit
                if local_sha and local_sha != "0000000000000000000000000000000000000000":
                    r = subprocess.run(
                        ["git", "log", "--format=%H", local_sha, "--not", "--remotes"],
                        cwd=str(repo_root), capture_output=True, text=True,
                    )
                    if r.returncode == 0 and r.stdout.strip():
                        commits.extend(r.stdout.strip().splitlines())
    except Exception:
        pass

    # stdin 已被读取，后续无法再读。如果没有获取到 commit，回退到 HEAD
    if not commits:
        try:
            r = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(repo_root), capture_output=True, text=True,
            )
            if r.returncode == 0:
                commits = [r.stdout.strip()]
        except Exception:
            pass

    return commits


def _push_to_server(
    server_url: str,
    result,
    repo_root: Path,
    project_name: str = None,
    ai_files: set = None,
    push_commits: list = None,
):
    """推送分析结果到服务器 - 每个 commit 单独一条记录，保留各自作者"""
    import json
    import subprocess
    from datetime import datetime

    def _git(args):
        r = subprocess.run(["git"] + args, cwd=str(repo_root), capture_output=True, text=True)
        return r.stdout.strip()

    if not project_name:
        project_name = repo_root.name

    ai_files = ai_files or set()

    # 构建每个文件的数据
    files_data = []
    for f in result.files:
        is_ai_modified = f.file_path in ai_files
        files_data.append({
            "path": f.file_path,
            "source": "ai" if is_ai_modified else "human",
            "ai_pure_lines": f.ai_pure_lines,
            "ai_modified_lines": f.ai_modified_lines,
            "mixed_lines": f.mixed_lines,
            "human_lines": f.human_lines,
            "ai_pure_chars": f.ai_pure_chars,
            "ai_modified_chars": f.ai_modified_chars,
            "mixed_chars": f.mixed_chars,
            "human_chars": f.human_chars,
        })

    # 获取 branch 信息
    branch_name = _git(["rev-parse", "--abbrev-ref", "HEAD"]) or ""

    # 按 commit 分别推送
    commits = push_commits or []
    if not commits:
        # fallback: 单 commit（HEAD）
        commits = [_git(["rev-parse", "HEAD"])]

    sent = 0
    for commit_hash in commits:
        if not commit_hash:
            continue

        author_name = _git(["log", "-1", "--format=%an", commit_hash]) or ""
        author_email = _git(["log", "-1", "--format=%ae", commit_hash]) or ""
        commit_time = _git(["log", "-1", "--format=%aI", commit_hash]) or datetime.utcnow().isoformat()

        payload = {
            "project_name": project_name,
            "project_path": str(repo_root),
            "commit_hash": commit_hash,
            "branch_name": branch_name,
            "author_name": author_name,
            "author_email": author_email,
            "commit_time": commit_time,
            "total_push_lines": result.total_push_lines,
            "ai_events_count": result.ai_events_count,
            "generation_rate": result.generation_rate,
            "retention_rate": result.retention_rate,
            "net_contribution": result.net_contribution,
            "ai_pure_lines": result.ai_pure_total,
            "ai_modified_lines": result.ai_modified_total,
            "mixed_lines": result.mixed_total,
            "human_lines": result.human_total,
            "deleted_ai_lines": result.deleted_ai_total,
            "ai_pure_chars": result.ai_pure_chars,
            "ai_modified_chars": result.ai_modified_chars,
            "mixed_chars": result.mixed_chars,
            "human_chars": result.human_chars,
            "total_chars": result.total_chars,
            "ai_generated_lines": result.ai_generated_lines,
            "ai_generated_chars": result.ai_generated_chars,
            "files": files_data,
        }

        try:
            import urllib.request
            req = urllib.request.Request(
                f"{server_url.rstrip('/')}/api/analysis",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                sent += 1
        except Exception as e:
            print(f"  Failed to push commit {commit_hash[:8]}: {e}", file=sys.stderr)

    if sent:
        print(f"  Pushed {sent} commit(s) to server: {server_url}")


def _cmd_report(args):
    """查询统计报告"""
    import json
    import urllib.request
    import urllib.parse

    server = args.server.rstrip('/')

    # 构建查询参数
    params = {}
    if args.project:
        params["project_name"] = args.project
    if args.author:
        params["author_name"] = args.author
    if args.from_date:
        params["from_date"] = args.from_date
    if args.to_date:
        params["to_date"] = args.to_date

    query = urllib.parse.urlencode(params) if params else ""

    # 获取汇总
    try:
        url = f"{server}/api/summary?{query}" if query else f"{server}/api/summary"
        with urllib.request.urlopen(url, timeout=10) as resp:
            summary = json.loads(resp.read().decode())
    except Exception as e:
        print(f"Failed to fetch summary: {e}", file=sys.stderr)
        return

    if args.json:
        print(json.dumps(summary, indent=2))
        return

    # 打印报告
    print()
    print("=" * 50)
    print("  AI 贡献统计报告")
    print("=" * 50)
    print()
    print(f"  总提交数：{summary.get('total_commits', 0)}")
    print(f"  总行数：{summary.get('total_lines', 0)}")
    print(f"  平均 AI 贡献：{summary.get('avg_ai_contribution', 0)*100:.1f}%")
    print()
    print("  明细:")
    print(f"    纯 AI:    {summary.get('ai_pure_total', 0)} 行")
    print(f"    AI 修改：{summary.get('ai_modified_total', 0)} 行")
    print(f"    混合：{summary.get('mixed_total', 0)} 行")
    print(f"    人工：{summary.get('human_total', 0)} 行")
    print()
    print("=" * 50)


if __name__ == "__main__":
    main()
