#!/usr/bin/env python3
"""Run the authorized synthetic/UI-TARS queue without interactive prompts.

The headless agent is allowed to finish only when it reports END and the OCR
watcher has produced a non-empty result file. CALL_USER, errors, timeouts, and
missing OCR results stop the queue instead of advancing to another person.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from task_queue import (
    QueueStore,
    Task,
    _write_task_files,
    initialize_from_csv,
    task_output_dir,
)


def build_agent_command(
    *, node: str, runner: Path, settings: Path, prompt: Path, status: Path
) -> list[str]:
    return [
        node,
        str(runner),
        "--settings",
        str(settings),
        "--prompt-file",
        str(prompt),
        "--status-file",
        str(status),
    ]


def read_agent_status(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def is_successful_agent_run(status: dict[str, Any], ocr_path: Path) -> bool:
    if str(status.get("status", "")).upper() != "END":
        return False
    try:
        content = ocr_path.read_text(encoding="utf-8")
    except OSError:
        return False
    return bool(content.strip()) and "图片数：0" not in content


def build_demo_prompt(task: Task, output_dir: Path) -> str:
    return f"""这是本地虚构数据演示任务，不要访问任何真实医院系统或外部网站。

请使用浏览器打开 http://127.0.0.1:8765，使用账号 demo、密码 demo 登录。
搜索患者编号 {task.patient_id}，核对姓名为 {task.name}，出生日期为 {task.birth_date or '名单未提供'}。

执行要求：
1. 只在这个本地演示网页中操作，不要打开 PyCharm、PowerShell 或项目文件寻找入口。
2. 打开该患者的全部演示记录，从记录顶部开始处理；页面稳定后让浏览器保持在前台，使用 hotkey(key='win print') 保存截图。
3. 截图应通过 Windows 截图功能产生，保存目录为：{output_dir}
4. 不要使用 PowerShell 命令截图，不要修改页面内容，不要处理名单中的下一位患者。
5. 所有记录完成并确认截图后，直接输出 finished() 表示任务完成；不要等待人工确认。
"""


def _start_child(command: list[str], project_root: Path) -> subprocess.Popen[bytes]:
    return subprocess.Popen(command, cwd=project_root)


def _stop_child(process: subprocess.Popen[bytes] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _wait_for_ocr(path: Path, timeout_seconds: int) -> bool:
    deadline = time.monotonic() + max(timeout_seconds, 0)
    while time.monotonic() <= deadline:
        if path.exists():
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                content = ""
            if content.strip() and "图片数：0" not in content:
                return True
        time.sleep(1)
    return False


def run_queue(args: argparse.Namespace) -> int:
    project_root = args.project_root.resolve()
    python = Path(sys.executable)
    initialize_from_csv(args.csv.resolve(), args.db.resolve())
    queue = QueueStore(args.db.resolve())
    queue.reset_running()

    args.output_root.mkdir(parents=True, exist_ok=True)
    args.prompt_file.parent.mkdir(parents=True, exist_ok=True)
    args.screenshot_source.mkdir(parents=True, exist_ok=True)

    while True:
        task = queue.claim_next()
        if task is None:
            return 0

        output_dir = task_output_dir(args.output_root, task.task_id)
        _write_task_files(task, args.output_root, args.prompt_file, args.task_id_file)
        status_file = output_dir / "agent-status.json"
        ocr_file = output_dir / "OCR.md"
        status_file.unlink(missing_ok=True)
        if args.demo_mode:
            args.prompt_file.write_text(build_demo_prompt(task, output_dir), encoding="utf-8")

        sync_process = _start_child(
            [
                str(python),
                str(project_root / "sync_windows_screenshots.py"),
                "--source",
                str(args.screenshot_source),
                "--target",
                str(output_dir),
                "--skip-existing",
                "--interval",
                "1",
            ],
            project_root,
        )
        ocr_process = _start_child(
            [
                str(python),
                str(project_root / "watch_ocr.py"),
                str(output_dir),
                "--output",
                str(ocr_file),
                "--config",
                str(args.ocr_config.resolve()),
            ],
            project_root,
        )
        agent_process: subprocess.Popen[bytes] | None = None
        try:
            agent_process = _start_child(
                build_agent_command(
                    node=args.node,
                    runner=args.agent_runner.resolve(),
                    settings=args.settings.resolve(),
                    prompt=args.prompt_file.resolve(),
                    status=status_file,
                ),
                project_root,
            )
            try:
                agent_process.wait(timeout=max(args.timeout_seconds, 1))
            except subprocess.TimeoutExpired:
                agent_process.kill()
                agent_process.wait(timeout=5)
                queue.mark(
                    task.task_id,
                    "waiting_manual",
                    "headless agent timed out; inspect the desktop and resume manually",
                )
                return 2

            status = read_agent_status(status_file)
            if str(status.get("status", "")).upper() == "CALL_USER":
                queue.mark(task.task_id, "waiting_manual", "agent requested user attention")
                return 2
            if str(status.get("status", "")).upper() == "ERROR":
                queue.mark(task.task_id, "failed", str(status.get("error", "agent error"))[:1000])
                return 1
            if not _wait_for_ocr(ocr_file, args.ocr_wait_seconds):
                queue.mark(task.task_id, "failed", "agent finished but OCR output was not produced")
                return 1
            if not is_successful_agent_run(status, ocr_file):
                queue.mark(task.task_id, "failed", "agent did not report END or OCR output was empty")
                return 1
            queue.mark(task.task_id, "done")
        finally:
            _stop_child(agent_process)
            _stop_child(sync_process)
            _stop_child(ocr_process)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the queue through headless UI-TARS and OCR")
    parser.add_argument("--project-root", type=Path, default=Path(__file__).parent)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--prompt-file", type=Path, required=True)
    parser.add_argument("--task-id-file", type=Path, default=Path("queue/current_task.id"))
    parser.add_argument("--ocr-config", type=Path, required=True)
    parser.add_argument("--screenshot-source", type=Path, required=True)
    parser.add_argument("--settings", type=Path, required=True)
    parser.add_argument("--agent-runner", type=Path, default=Path("ui_tars_agent_runner.mjs"))
    parser.add_argument("--node", default="node")
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--ocr-wait-seconds", type=int, default=120)
    parser.add_argument("--demo-mode", action="store_true")
    return parser


def main() -> int:
    args = _parser().parse_args()
    try:
        return run_queue(args)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"自动队列失败：{error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
