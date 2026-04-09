#!/usr/bin/env python3
"""
XHS Operations Dashboard - Flask Backend
Port: 5800
"""

import json
import os
import re
import signal
import subprocess
import threading
import time
import fcntl
from datetime import datetime, timedelta
from pathlib import Path
from glob import glob as globfiles

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
WORKSPACE = Path("/Users/sd3/xhs-workspace")
DASHBOARD_DIR = WORKSPACE / "dashboard"
TASKS_FILE = DASHBOARD_DIR / "tasks.json"
LOGS_DIR = WORKSPACE / "logs"
ANALYTICS_DIR = WORKSPACE / "analytics"
PUBLISHED_DIR = WORKSPACE / "published"
DRAFTS_DIR = WORKSPACE / "drafts"
CONTENT_CAL_DIR = WORKSPACE / "content-calendar"
STRATEGY_FILE = WORKSPACE / "strategy.json"
SKILL_DIR = WORKSPACE / "xiaohongshu-skill"
CLI_PATH = SKILL_DIR / "scripts" / "cli.py"

# ---------------------------------------------------------------------------
# Flask app
# ---------------------------------------------------------------------------
app = Flask(
    __name__,
    template_folder=str(DASHBOARD_DIR / "templates"),
    static_folder=str(DASHBOARD_DIR / "static"),
)
CORS(app)

# ---------------------------------------------------------------------------
# In-memory state
# ---------------------------------------------------------------------------
_running_procs: dict[str, subprocess.Popen] = {}  # task_id -> Popen
_login_cache: dict = {"ts": 0, "data": None}
_accounts_cache: dict = {"ts": 0, "data": None}
LOGIN_CACHE_TTL = 60  # seconds
ACCOUNTS_CACHE_TTL = 60  # seconds

LOCK_PATH = TASKS_FILE.with_suffix(".lock")

# ---------------------------------------------------------------------------
# Helpers - tasks.json with file locking
# ---------------------------------------------------------------------------

def _read_tasks() -> dict:
    """Read tasks.json under a shared lock."""
    if not TASKS_FILE.exists():
        return {"tasks": []}
    lock_fd = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_SH)
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def _write_tasks(data: dict) -> None:
    """Write tasks.json under an exclusive lock."""
    lock_fd = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()


def _find_task(data: dict, task_id: str):
    """Return (index, task_dict) or (None, None)."""
    for i, t in enumerate(data.get("tasks", [])):
        if t["id"] == task_id:
            return i, t
    return None, None


def _slugify(name: str) -> str:
    """Simple slug: lowercase ascii + dashes, fallback to timestamp."""
    slug = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", name).strip("-").lower()
    if not slug:
        slug = f"task-{int(time.time())}"
    return slug


def _today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Startup: reconcile stale "running" tasks
# ---------------------------------------------------------------------------

def _reconcile_running_tasks():
    """On startup, mark tasks with status 'running' but no live process as 'failed'."""
    data = _read_tasks()
    changed = False
    for task in data.get("tasks", []):
        if task.get("status") == "running":
            pid = task.get("pid")
            alive = False
            if pid:
                try:
                    os.kill(pid, 0)
                    alive = True
                except OSError:
                    alive = False
            if not alive:
                task["status"] = "failed"
                task["last_result"] = "Process not found on server restart"
                task["pid"] = None
                changed = True
    if changed:
        _write_tasks(data)


# ---------------------------------------------------------------------------
# Background task runner
# ---------------------------------------------------------------------------

def _run_task_background(task_id: str, prompt: str):
    """Execute claude CLI in background, update tasks.json on completion."""
    date_str = _today_str()
    log_path = LOGS_DIR / f"task-{task_id}-{date_str}.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    start_time = time.time()

    try:
        with open(log_path, "a", encoding="utf-8") as log_f:
            log_f.write(f"\n{'='*60}\n")
            log_f.write(f"Task: {task_id}  Started: {datetime.now().isoformat()}\n")
            log_f.write(f"{'='*60}\n\n")
            log_f.flush()

            env = {**os.environ,
                   "http_proxy": "http://127.0.0.1:7890",
                   "https_proxy": "http://127.0.0.1:7890",
                   "all_proxy": "socks5://127.0.0.1:7890"}
            proc = subprocess.Popen(
                [
                    "claude",
                    "-p",
                    prompt,
                    "--dangerously-skip-permissions",
                    "--output-format",
                    "text",
                ],
                cwd=str(WORKSPACE),
                env=env,
                stdout=log_f,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,  # new process group for clean kill
            )

        # Register
        _running_procs[task_id] = proc

        # Update tasks.json with PID
        data = _read_tasks()
        _, task = _find_task(data, task_id)
        if task:
            task["pid"] = proc.pid
            _write_tasks(data)

        # Wait for completion
        proc.wait()
        duration = round(time.time() - start_time, 1)
        status = "completed" if proc.returncode == 0 else "failed"

        # Read last few lines as result summary
        try:
            with open(log_path, "r", encoding="utf-8") as lf:
                lines = lf.readlines()
                summary_lines = [l.strip() for l in lines[-5:] if l.strip()]
                summary = "\n".join(summary_lines)[:500]
        except Exception:
            summary = f"exit code {proc.returncode}"

    except Exception as exc:
        duration = round(time.time() - start_time, 1)
        status = "failed"
        summary = str(exc)[:500]

    finally:
        _running_procs.pop(task_id, None)

    # Persist final state
    data = _read_tasks()
    _, task = _find_task(data, task_id)
    if task:
        task["status"] = status
        task["last_run"] = datetime.now().isoformat()
        task["last_duration"] = duration
        task["last_result"] = summary
        task["pid"] = None
        _write_tasks(data)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html")


# ---- Status ---------------------------------------------------------------

@app.route("/api/status")
def api_status():
    now = time.time()
    if _login_cache["data"] is not None and (now - _login_cache["ts"]) < LOGIN_CACHE_TTL:
        return jsonify(_login_cache["data"])

    try:
        result = subprocess.run(
            ["python", str(CLI_PATH), "check-login"],
            cwd=str(SKILL_DIR),
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        # Try to parse JSON from output
        try:
            parsed = json.loads(output)
            logged_in = parsed.get("logged_in", False)
            account = parsed.get("account") or parsed.get("nickname")
        except json.JSONDecodeError:
            # Heuristic: look for keywords
            logged_in = "logged in" in output.lower() or "已登录" in output
            account = None

        data = {"logged_in": logged_in, "account": account}
    except subprocess.TimeoutExpired:
        data = {"logged_in": False, "account": None, "error": "check-login timed out"}
    except Exception as e:
        data = {"logged_in": False, "account": None, "error": str(e)}

    _login_cache["ts"] = now
    _login_cache["data"] = data
    return jsonify(data)


# ---- Tasks CRUD -----------------------------------------------------------

@app.route("/api/tasks", methods=["GET"])
def api_tasks_list():
    data = _read_tasks()
    return jsonify(data.get("tasks", []))


@app.route("/api/tasks", methods=["POST"])
def api_tasks_create():
    body = request.get_json(force=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    name = body.get("name", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    task_id = _slugify(name)
    data = _read_tasks()

    # Ensure unique id
    existing_ids = {t["id"] for t in data.get("tasks", [])}
    base_id = task_id
    counter = 2
    while task_id in existing_ids:
        task_id = f"{base_id}-{counter}"
        counter += 1

    task = {
        "id": task_id,
        "name": name,
        "phase": body.get("phase", 0),
        "cron_expr": body.get("cron_expr", "0 * * * *"),
        "prompt": body.get("prompt", ""),
        "enabled": True,
        "status": "idle",
        "last_run": None,
        "last_duration": None,
        "last_result": None,
        "pid": None,
    }

    data.setdefault("tasks", []).append(task)
    _write_tasks(data)
    _sync_crontab()
    return jsonify(task), 201


@app.route("/api/tasks/<task_id>", methods=["PUT"])
def api_tasks_update(task_id: str):
    body = request.get_json(force=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    data = _read_tasks()
    idx, task = _find_task(data, task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    allowed = {"name", "cron_expr", "prompt", "enabled", "phase"}
    for key in allowed:
        if key in body:
            task[key] = body[key]

    # If disabled, set status accordingly
    if task.get("enabled") is False and task.get("status") == "idle":
        task["status"] = "disabled"
    elif task.get("enabled") is True and task.get("status") == "disabled":
        task["status"] = "idle"

    data["tasks"][idx] = task
    _write_tasks(data)
    _sync_crontab()
    return jsonify(task)


@app.route("/api/tasks/<task_id>", methods=["DELETE"])
def api_tasks_delete(task_id: str):
    data = _read_tasks()
    idx, task = _find_task(data, task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    # If running, stop first
    if task_id in _running_procs:
        _stop_process(task_id)

    data["tasks"].pop(idx)
    _write_tasks(data)
    _sync_crontab()
    return jsonify({"deleted": task_id})


# ---- Run / Stop -----------------------------------------------------------

@app.route("/api/tasks/<task_id>/run", methods=["POST"])
def api_tasks_run(task_id: str):
    data = _read_tasks()
    idx, task = _find_task(data, task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    if task.get("status") == "running":
        return jsonify({"error": "task is already running", "pid": task.get("pid")}), 409

    # Mark running
    task["status"] = "running"
    task["last_run"] = datetime.now().isoformat()
    task["last_result"] = None
    task["last_duration"] = None
    data["tasks"][idx] = task
    _write_tasks(data)

    # Launch in background thread
    thread = threading.Thread(
        target=_run_task_background,
        args=(task_id, task["prompt"]),
        daemon=True,
    )
    thread.start()

    # Wait briefly so PID is available
    time.sleep(0.3)
    data = _read_tasks()
    _, updated = _find_task(data, task_id)
    pid = updated.get("pid") if updated else None

    return jsonify({"status": "started", "pid": pid})


def _stop_process(task_id: str):
    """Send SIGTERM then SIGKILL to a running task."""
    proc = _running_procs.get(task_id)
    if proc is None:
        # Try from tasks.json PID
        data = _read_tasks()
        _, task = _find_task(data, task_id)
        pid = task.get("pid") if task else None
        if pid:
            try:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass
            # Wait then force kill
            time.sleep(5)
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except (OSError, ProcessLookupError):
                pass
        return

    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (OSError, ProcessLookupError):
        pass

    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (OSError, ProcessLookupError):
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass

    _running_procs.pop(task_id, None)


@app.route("/api/tasks/<task_id>/stop", methods=["POST"])
def api_tasks_stop(task_id: str):
    data = _read_tasks()
    idx, task = _find_task(data, task_id)
    if task is None:
        return jsonify({"error": "task not found"}), 404

    _stop_process(task_id)

    # Update state
    data = _read_tasks()
    idx, task = _find_task(data, task_id)
    if task:
        task["status"] = "idle"
        task["pid"] = None
        data["tasks"][idx] = task
        _write_tasks(data)

    return jsonify({"status": "stopped", "task_id": task_id})


# ---- Logs -----------------------------------------------------------------

def _parse_log_line(line: str) -> dict:
    """Parse a log line into {time, message, level} for frontend."""
    line = line.rstrip("\n").rstrip()
    if not line:
        return None
    # Try to extract timestamp like [2026-03-18T23:07:40]
    time_str = ""
    level = "info"
    msg = line
    if line.startswith("[") and "]" in line:
        bracket_end = line.index("]")
        time_str = line[1:bracket_end]
        msg = line[bracket_end + 1:].strip()
    # Detect level from content
    lower = msg.lower()
    if any(w in lower for w in ["error", "failed", "异常", "失败", "超时"]):
        level = "error"
    elif any(w in lower for w in ["success", "completed", "成功", "完成", "✅"]):
        level = "success"
    elif any(w in lower for w in ["warning", "warn", "skip", "跳过", "注意"]):
        level = "warning"
    return {"time": time_str, "message": msg, "level": level}


def _read_task_logs(date: str, task_id: str = None) -> list:
    """Read task log files and return structured log entries."""
    logs = []
    if task_id:
        patterns = [f"task-{task_id}-{date}.log"]
    else:
        patterns = [p.name for p in sorted(LOGS_DIR.glob(f"task-*-{date}.log"))]

    for fname in patterns:
        fpath = LOGS_DIR / fname
        if not fpath.exists():
            continue
        try:
            text = fpath.read_text(encoding="utf-8")[-20000:]
            for line in text.split("\n"):
                parsed = _parse_log_line(line)
                if parsed:
                    parsed["source"] = fname
                    logs.append(parsed)
        except Exception:
            pass
    return logs


def _read_interact_logs(date: str) -> list:
    """Read interaction log and return structured entries."""
    logs = []
    fpath = LOGS_DIR / f"interact-{date}.json"
    if not fpath.exists():
        return logs
    try:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else data.get("actions", data.get("interactions", []))
        for item in items:
            ts = item.get("timestamp", item.get("time", ""))
            action = item.get("type", item.get("action", "互动"))
            feed = item.get("feed_id", "")
            author = item.get("author", "")
            content = item.get("content", "")
            detail = f"[{action}] "
            if author:
                detail += f"@{author} "
            if feed:
                detail += f"feed:{feed[:12]}... "
            if content:
                detail += content[:60]
            logs.append({
                "time": ts[11:19] if len(ts) > 19 else ts,
                "message": detail.strip(),
                "level": "success" if action in ("comment", "like", "评论", "点赞") else "info",
                "source": "interact",
            })
    except Exception:
        pass
    return logs


def _read_notification_logs(date: str) -> list:
    """Read notification log and return structured entries."""
    logs = []
    fpath = LOGS_DIR / f"notification-{date}.json"
    if not fpath.exists():
        return logs
    try:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        # Handle different formats
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("replies", data.get("actions", []))
            # Also show replied_ids summary
            replied = data.get("replied_ids", [])
            if replied and not items:
                logs.append({
                    "time": "",
                    "message": f"已回复 {len(replied)} 条通知",
                    "level": "info",
                    "source": "notification",
                })
        for item in items:
            ts = item.get("timestamp", item.get("time", ""))
            action = item.get("action", "reply")
            content = item.get("content", item.get("reply", ""))
            user = item.get("user", item.get("from", ""))
            msg = f"[{action}] "
            if user:
                msg += f"@{user} "
            if content:
                msg += str(content)[:80]
            logs.append({
                "time": ts[11:19] if len(ts) > 19 else ts,
                "message": msg.strip(),
                "level": "success",
                "source": "notification",
            })
    except Exception:
        pass
    return logs


def _read_cdp_logs(date: str, task_id: str = None) -> list:
    """Extract CDP/browser-related log lines from task logs and cron logs."""
    import re
    logs = []
    cdp_patterns = re.compile(
        r"(cdp|chrome|websocket|ws://|devtools|browser|连接|断开|重连|cookie|login|logged|session|"
        r"CDP|Chrome|WebSocket|DevTools|Browser|版本|version|端口|port|启动|关闭|超时|timeout|"
        r"check-login|check_login|logged_in|qrcode|二维码|扫码|headless)",
        re.IGNORECASE,
    )

    # Scan task log files for this date
    if task_id:
        patterns = [f"task-{task_id}-{date}.log"]
    else:
        patterns = [p.name for p in sorted(LOGS_DIR.glob(f"task-*-{date}.log"))]

    # Also include cron logs
    for cron_log in sorted(LOGS_DIR.glob("cron-*.log")):
        patterns.append(cron_log.name)

    for fname in patterns:
        fpath = LOGS_DIR / fname
        if not fpath.exists():
            continue
        try:
            text = fpath.read_text(encoding="utf-8")[-30000:]
            for line in text.split("\n"):
                stripped = line.strip()
                if not stripped:
                    continue
                if cdp_patterns.search(stripped):
                    parsed = _parse_log_line(stripped)
                    if parsed:
                        # Override level for CDP-specific lines
                        lower = stripped.lower()
                        if "连接" in lower or "connect" in lower or "logged_in.*true" in lower:
                            parsed["level"] = "success"
                        elif "error" in lower or "失败" in lower or "断开" in lower or "not logged" in lower.replace("_", " "):
                            parsed["level"] = "error"
                        elif "warn" in lower or "重连" in lower or "retry" in lower:
                            parsed["level"] = "warning"
                        parsed["source"] = fname
                        logs.append(parsed)
        except Exception:
            pass
    return logs


@app.route("/api/logs")
def api_logs():
    date = request.args.get("date", _today_str())
    task_id = request.args.get("task_id") or None
    category = request.args.get("category", "task")

    logs = []
    if category == "task":
        logs = _read_task_logs(date, task_id)
    elif category == "interact":
        logs = _read_interact_logs(date)
    elif category == "notification":
        logs = _read_notification_logs(date)
    elif category == "cdp":
        logs = _read_cdp_logs(date, task_id)
    else:
        logs = _read_task_logs(date, task_id) + _read_interact_logs(date) + _read_notification_logs(date)

    return jsonify({"logs": logs})


@app.route("/api/cli-log")
def api_cli_log():
    """实时读取 cli.log 尾部，支持 ?lines=N&after=OFFSET 参数。"""
    cli_log_path = LOGS_DIR / "cli.log"
    lines_count = int(request.args.get("lines", 100))
    after_offset = int(request.args.get("after", 0))

    if not cli_log_path.exists():
        return jsonify({"lines": [], "offset": 0, "size": 0})

    try:
        file_size = cli_log_path.stat().st_size

        if after_offset > 0 and after_offset < file_size:
            # 增量读取：从上次偏移量开始
            with open(cli_log_path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(after_offset)
                new_content = f.read()
            raw_lines = [l for l in new_content.split("\n") if l.strip()]
        else:
            # 全量读取尾部
            read_size = min(file_size, 100_000)  # 最多读100KB
            with open(cli_log_path, "rb") as f:
                f.seek(max(0, file_size - read_size))
                raw = f.read().decode("utf-8", errors="replace")
            raw_lines = [l for l in raw.split("\n") if l.strip()]
            raw_lines = raw_lines[-lines_count:]

        # 解析每行，标记级别和高亮
        parsed = []
        for line in raw_lines:
            level = "info"
            lower = line.lower()
            if " error " in lower or "失败" in lower or "traceback" in lower:
                level = "error"
            elif " warning " in lower or "警告" in lower:
                level = "warning"
            elif "成功" in lower or "success" in lower or "发布完成" in lower:
                level = "success"
            elif "连接" in lower or "导航" in lower:
                level = "cdp"
            parsed.append({"text": line, "level": level})

        return jsonify({
            "lines": parsed,
            "offset": file_size,
            "size": file_size,
        })
    except Exception as e:
        return jsonify({"error": str(e), "lines": [], "offset": 0}), 500


@app.route("/api/daemon-status")
def api_daemon_status():
    """读取守护进程状态。"""
    state_file = LOGS_DIR / "daemon-state.json"
    pid_file = LOGS_DIR / "daemon.pid"

    result = {"running": False, "pid": None, "state": None}

    # 检查 PID
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)  # 检查进程是否存在
            result["running"] = True
            result["pid"] = pid
        except (ValueError, OSError):
            result["running"] = False

    # 读取状态
    if state_file.exists():
        try:
            with open(state_file, encoding="utf-8") as f:
                result["state"] = json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    return jsonify(result)


@app.route("/api/logs/live/<task_id>")
def api_logs_live(task_id: str):
    date = _today_str()
    # Support "latest" - find most recently modified task log
    if task_id == "latest":
        task_logs = sorted(LOGS_DIR.glob(f"task-*-{date}.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not task_logs:
            return jsonify({"logs": []})
        log_file = task_logs[0]
    else:
        log_file = LOGS_DIR / f"task-{task_id}-{date}.log"

    if not log_file.exists():
        return jsonify({"logs": []})

    try:
        text = log_file.read_text(encoding="utf-8")[-10000:]
        lines = text.split("\n")[-100:]
        logs = []
        for line in lines:
            parsed = _parse_log_line(line)
            if parsed:
                logs.append(parsed)
        return jsonify({"logs": logs})
    except Exception as e:
        return jsonify({"logs": [], "error": str(e)})


# ---- Analytics ------------------------------------------------------------

@app.route("/api/analytics")
def api_analytics():
    today = _today_str()
    result = {
        "today": None,
        "last_7_days": [],
        "published_count": 0,
        "total_interactions": 0,
    }

    # Today's analytics
    today_file = ANALYTICS_DIR / f"{today}.json"
    if today_file.exists():
        try:
            result["today"] = json.loads(today_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Last 7 days
    for i in range(7):
        d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        f = ANALYTICS_DIR / f"{d}.json"
        if f.exists():
            try:
                day_data = json.loads(f.read_text(encoding="utf-8"))
                day_data["_date"] = d
                result["last_7_days"].append(day_data)
            except Exception:
                pass

    # Published notes count
    pub_files = list(PUBLISHED_DIR.glob("*.json"))
    result["published_count"] = len(pub_files)

    # Total interactions from interact logs
    total = 0
    for f in LOGS_DIR.glob("interact-*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(data, list):
                total += len(data)
            elif isinstance(data, dict):
                total += len(data.get("actions", data.get("interactions", [])))
        except Exception:
            pass
    result["total_interactions"] = total

    return jsonify(result)


# ---- Timeline & Activity & Dashboard Stats --------------------------------

@app.route("/api/timeline")
def api_timeline():
    """Today's task schedule as timeline entries."""
    data = _read_tasks()
    timeline = []
    for t in data.get("tasks", []):
        if not t.get("enabled", True):
            continue
        cron = t.get("cron_expr", "")
        parts = cron.split()
        if len(parts) >= 2:
            minute, hour = parts[0], parts[1]
            time_str = f"{hour.zfill(2)}:{minute.zfill(2)}"
        else:
            time_str = "??:??"
        timeline.append({
            "id": t["id"],
            "name": t["name"],
            "time": time_str,
            "phase": t.get("phase"),
            "status": t.get("status", "idle"),
            "last_run": t.get("last_run"),
            "last_result": t.get("last_result"),
        })
    timeline.sort(key=lambda x: x["time"])
    return jsonify(timeline)


@app.route("/api/activity")
def api_activity():
    """Recent activity entries from logs."""
    today = _today_str()
    activities = []

    # Task logs from today
    for f in sorted(LOGS_DIR.glob(f"task-*-{today}.log"), reverse=True):
        try:
            lines = f.read_text(encoding="utf-8").strip().split("\n")
            for line in lines[-10:]:
                activities.append({
                    "type": "task",
                    "source": f.stem,
                    "message": line.strip(),
                    "timestamp": today,
                })
        except Exception:
            pass

    # Interaction logs
    interact_file = LOGS_DIR / f"interact-{today}.json"
    if interact_file.exists():
        try:
            data = json.loads(interact_file.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else data.get("actions", [])
            for item in items[-10:]:
                activities.append({
                    "type": "interact",
                    "source": "interact",
                    "message": str(item.get("type", "")) + ": " + str(item.get("feed_id", "")),
                    "timestamp": item.get("timestamp", today),
                })
        except Exception:
            pass

    # Notification logs
    notif_file = LOGS_DIR / f"notification-{today}.json"
    if notif_file.exists():
        try:
            data = json.loads(notif_file.read_text(encoding="utf-8"))
            items = data if isinstance(data, list) else data.get("replies", [])
            for item in items[-5:]:
                activities.append({
                    "type": "notification",
                    "source": "notification",
                    "message": str(item.get("action", "reply")) + ": " + str(item.get("content", "")[:50]),
                    "timestamp": item.get("timestamp", today),
                })
        except Exception:
            pass

    return jsonify(activities[-20:])


_dashboard_cache: dict = {"ts": 0, "data": None}
DASHBOARD_CACHE_TTL = 120  # 2 minutes


@app.route("/api/dashboard/stats")
def api_dashboard_stats():
    """Full dashboard stats from CLI get-dashboard + local files."""
    now = time.time()

    # Use cache if fresh
    if _dashboard_cache["data"] and now - _dashboard_cache["ts"] < DASHBOARD_CACHE_TTL:
        return jsonify(_dashboard_cache["data"])

    today = _today_str()
    result: dict = {
        "followers": "--",
        "followersChange": "+0",
        "followersChangeType": "flat",
        "impressions": "--",
        "impressionsChange": "+0",
        "impressionsChangeType": "flat",
        "interactions": "--",
        "interactionsChange": "+0",
        "interactionsChangeType": "flat",
        "ctr": "--",
        "ctrChange": "+0%",
        "ctrChangeType": "flat",
        "commentsToday": 0,
        "likesToday": 0,
        "publishesToday": 0,
    }

    # Try CLI get-dashboard
    try:
        proc = subprocess.run(
            ["python", str(CLI_PATH), "get-dashboard"],
            capture_output=True, text=True, timeout=60,
        )
        if proc.returncode == 0:
            cli_data = json.loads(proc.stdout)
            account = cli_data.get("account", {})
            overview = cli_data.get("overview_7d", {})
            trends = overview.get("trends", {})
            diagnosis = cli_data.get("diagnosis", {})

            result["followers"] = account.get("followers", "--")

            # Followers change
            net = overview.get("net_followers", "0")
            net_str = str(net)
            if net_str.startswith("-"):
                result["followersChange"] = net_str
                result["followersChangeType"] = "down"
            elif net_str != "0":
                result["followersChange"] = f"+{net_str}"
                result["followersChangeType"] = "up"

            result["impressions"] = overview.get("impressions", "--")
            imp_trend = trends.get("impressions", "+0%")
            result["impressionsChange"] = imp_trend
            result["impressionsChangeType"] = "down" if imp_trend.startswith("-") else ("up" if not imp_trend.startswith("+0") and imp_trend.startswith("+") else "flat")

            # Interactions = likes + comments + favorites + shares
            try:
                interactions = int(overview.get("likes", 0)) + int(overview.get("comments", 0)) + int(overview.get("favorites", 0)) + int(overview.get("shares", 0))
                result["interactions"] = interactions
            except (ValueError, TypeError):
                pass

            # Interactions percentile from diagnosis
            diag_interact = diagnosis.get("互动", {})
            if diag_interact.get("percentile"):
                result["interactionsChange"] = f"Top {100 - diag_interact['percentile']}%"
                result["interactionsChangeType"] = "up"

            result["ctr"] = overview.get("cover_ctr", "--")
            ctr_trend = trends.get("cover_ctr", "+0%")
            result["ctrChange"] = ctr_trend
            result["ctrChangeType"] = "down" if ctr_trend.startswith("-") else ("up" if not ctr_trend.startswith("+0") and ctr_trend.startswith("+") else "flat")

    except Exception as e:
        app.logger.warning("get-dashboard failed: %s", e)

    # Today's quota from daily-quota.json
    quota_file = LOGS_DIR / "daily-quota.json"
    if quota_file.exists():
        try:
            qdata = json.loads(quota_file.read_text(encoding="utf-8"))
            if qdata.get("date") == today:
                counts = qdata.get("counts", {})
                result["commentsToday"] = counts.get("comment", 0)
                result["likesToday"] = counts.get("like", 0)
                result["publishesToday"] = counts.get("publish", 0)
        except Exception:
            pass

    # Today published count
    result["publishesToday"] = max(
        result["publishesToday"],
        len(list(PUBLISHED_DIR.glob(f"{today}-*.json"))),
    )

    _dashboard_cache["ts"] = now
    _dashboard_cache["data"] = result
    return jsonify(result)


@app.route("/api/schedule/crontab")
def api_schedule_crontab():
    """Return current crontab content."""
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return jsonify({"raw": "", "entries": []})
        lines = result.stdout.strip().split("\n")
        xhs_entries = [l for l in lines if "xhs" in l.lower() or "run-phase" in l.lower()]
        return jsonify({"raw": result.stdout, "entries": xhs_entries})
    except Exception:
        return jsonify({"raw": "", "entries": []})


# ---- Published ------------------------------------------------------------

@app.route("/api/published")
def api_published():
    notes = []
    for f in sorted(PUBLISHED_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_filename"] = f.name
            notes.append(data)
        except Exception:
            pass
    return jsonify(notes)


# ---- Schedule (crontab) ---------------------------------------------------

@app.route("/api/schedule")
def api_schedule():
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return jsonify({"entries": [], "raw": "", "error": "no crontab"})

        lines = result.stdout.strip().split("\n")
        xhs_entries = [l for l in lines if "xhs" in l.lower() or "run-phase" in l.lower()]
        return jsonify({
            "entries": xhs_entries,
            "raw": result.stdout,
        })
    except Exception as e:
        return jsonify({"entries": [], "raw": "", "error": str(e)})


def _sync_crontab():
    """Internal: sync tasks.json to system crontab. Called automatically on task changes."""
    data = _read_tasks()
    enabled_tasks = [t for t in data.get("tasks", []) if t.get("enabled")]
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=10)
        existing = result.stdout if result.returncode == 0 else ""
    except Exception:
        existing = ""
    non_xhs_lines = []
    for line in existing.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            if "xhs" not in stripped.lower() and "run-phase" not in stripped.lower():
                non_xhs_lines.append(line)
            continue
        if "xhs" not in line.lower() and "run-phase" not in line.lower():
            non_xhs_lines.append(line)
    run_script = DASHBOARD_DIR / "run-phase.sh"
    xhs_lines = [f"# --- XHS Dashboard Tasks (auto-synced {datetime.now().isoformat()}) ---"]
    for t in enabled_tasks:
        cron = t["cron_expr"]
        tid = t["id"]
        log_file = LOGS_DIR / f"cron-{tid}.log"
        entry = f'{cron} cd {WORKSPACE} && {run_script} {tid} >> {log_file} 2>&1'
        xhs_lines.append(entry)
    xhs_lines.append("# --- End XHS Dashboard Tasks ---")
    new_crontab = "\n".join(non_xhs_lines + [""] + xhs_lines) + "\n"
    proc = subprocess.run(["crontab", "-"], input=new_crontab, capture_output=True, text=True, timeout=10)
    return proc.returncode == 0, len(enabled_tasks)


@app.route("/api/schedule/sync", methods=["POST"])
def api_schedule_sync():
    data = _read_tasks()
    enabled_tasks = [t for t in data.get("tasks", []) if t.get("enabled")]

    # Read existing crontab
    try:
        result = subprocess.run(
            ["crontab", "-l"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        existing = result.stdout if result.returncode == 0 else ""
    except Exception:
        existing = ""

    # Separate non-xhs entries
    non_xhs_lines = []
    for line in existing.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            # Keep comments that are not xhs-related
            if "xhs" not in stripped.lower() and "run-phase" not in stripped.lower():
                non_xhs_lines.append(line)
            continue
        if "xhs" not in line.lower() and "run-phase" not in line.lower():
            non_xhs_lines.append(line)

    # Generate new xhs entries
    run_script = DASHBOARD_DIR / "run-phase.sh"
    xhs_lines = [
        f"# --- XHS Dashboard Tasks (auto-synced {datetime.now().isoformat()}) ---"
    ]
    for t in enabled_tasks:
        cron = t["cron_expr"]
        tid = t["id"]
        log_file = LOGS_DIR / f"cron-{tid}.log"
        entry = f'{cron} cd {WORKSPACE} && {run_script} {tid} >> {log_file} 2>&1'
        xhs_lines.append(entry)
    xhs_lines.append("# --- End XHS Dashboard Tasks ---")

    # Combine
    new_crontab = "\n".join(non_xhs_lines + [""] + xhs_lines) + "\n"

    # Write
    try:
        proc = subprocess.run(
            ["crontab", "-"],
            input=new_crontab,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if proc.returncode != 0:
            return jsonify({"error": proc.stderr}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({
        "synced": len(enabled_tasks),
        "tasks": [t["id"] for t in enabled_tasks],
    })


# ---- Drafts ---------------------------------------------------------------

@app.route("/api/drafts")
def api_drafts():
    """Read all drafts from drafts/ directory."""
    drafts = []
    seen_bases = set()

    # 1. JSON draft files
    for f in sorted(DRAFTS_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            base = f.stem  # e.g. 2026-03-13-001
            seen_bases.add(base)
            word_count = 0
            # Try to get word count from content file or summary
            content_file = DRAFTS_DIR / f"{base}-content.txt"
            if content_file.exists():
                word_count = len(content_file.read_text(encoding="utf-8"))
            elif data.get("content_summary"):
                word_count = len(data["content_summary"])
            drafts.append({
                "filename": f.name,
                "title": data.get("title") or data.get("topic", f.stem),
                "format": data.get("type", data.get("format", "图文")),
                "created": data.get("drafted_at", data.get("date", "")),
                "word_count": word_count,
                "status": data.get("status", "draft"),
            })
        except Exception:
            pass

    # 2. Title+content txt pairs without JSON
    for tf in sorted(DRAFTS_DIR.glob("*-title.txt"), reverse=True):
        base = tf.stem.replace("-title", "")
        if base in seen_bases:
            continue
        try:
            title = tf.read_text(encoding="utf-8").strip()
            word_count = 0
            content_file = DRAFTS_DIR / f"{base}-content.txt"
            if content_file.exists():
                word_count = len(content_file.read_text(encoding="utf-8"))
            drafts.append({
                "filename": tf.name,
                "title": title or base,
                "format": "图文",
                "created": base[:10] if len(base) >= 10 else "",
                "word_count": word_count,
                "status": "draft",
            })
        except Exception:
            pass

    return jsonify({"drafts": drafts})


# ---- Content Calendar -----------------------------------------------------

@app.route("/api/content-calendar")
def api_content_calendar():
    """Read content calendar for a given month."""
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    items = []
    pattern = f"{month}-*.json"

    for f in sorted(CONTENT_CAL_DIR.glob(pattern)):
        if "-research" in f.name:
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            date_str = data.get("date", f.stem)
            topics = []
            candidates = data.get("candidates", [])
            for i, c in enumerate(candidates):
                topics.append({
                    "seq": i + 1,
                    "title": c.get("title_draft", c.get("title", "")),
                    "type": c.get("type", ""),
                    "pillar": c.get("pillar", ""),
                    "format": c.get("format", "图文"),
                    "publish_time": c.get("publish_time", ""),
                    "status": "selected" if c.get("selected") else "candidate",
                })
            if not candidates:
                # Single-topic format
                topics.append({
                    "seq": 1,
                    "title": data.get("title", data.get("topic", "")),
                    "type": data.get("type", ""),
                    "pillar": data.get("pillar", ""),
                    "format": data.get("format", "图文"),
                    "publish_time": data.get("publish_time", ""),
                    "status": data.get("status", "planned"),
                })
            items.append({"date": date_str, "topics": topics})
        except Exception:
            pass

    return jsonify({"items": items})


# ---- Interact Index -------------------------------------------------------

@app.route("/api/interact-index")
def api_interact_index():
    """Read interacted-index.json."""
    fpath = LOGS_DIR / "interacted-index.json"
    if not fpath.exists():
        return jsonify({"feeds": {}})
    try:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        return jsonify(data)
    except Exception as e:
        return jsonify({"feeds": {}, "error": str(e)})


# ---- Notifications --------------------------------------------------------

@app.route("/api/notifications")
def api_notifications():
    """Read the most recent notification file."""
    notif_files = sorted(LOGS_DIR.glob("notification-????-??-??.json"), reverse=True)
    if not notif_files:
        return jsonify({"date": None, "replied_ids": [], "count": 0})
    try:
        latest = notif_files[0]
        data = json.loads(latest.read_text(encoding="utf-8"))
        date_str = latest.stem.replace("notification-", "")
        replied = data.get("replied_ids", [])
        return jsonify({
            "date": date_str,
            "replied_ids": replied,
            "count": len(replied),
            "data": data,
        })
    except Exception as e:
        return jsonify({"date": None, "replied_ids": [], "count": 0, "error": str(e)})


# ---- Quota ----------------------------------------------------------------

@app.route("/api/quota")
def api_quota():
    """Read daily quota and combine with strategy limits."""
    quota_file = LOGS_DIR / "daily-quota.json"
    counts = {"comment": 0, "like": 0, "publish": 0, "favorite": 0}
    quota_date = _today_str()

    if quota_file.exists():
        try:
            data = json.loads(quota_file.read_text(encoding="utf-8"))
            quota_date = data.get("date", quota_date)
            raw_counts = data.get("counts", {})
            counts.update({k: raw_counts.get(k, 0) for k in counts})
        except Exception:
            pass

    # Limits from CLAUDE.md / strategy safety section
    limits = {"comment": 100, "like": 50, "publish": 4, "favorite": 50}
    if STRATEGY_FILE.exists():
        try:
            strat = json.loads(STRATEGY_FILE.read_text(encoding="utf-8"))
            safety = strat.get("safety", {})
            if "daily_comment_limit" in safety:
                limits["comment"] = safety["daily_comment_limit"]
            if "daily_like_limit" in safety:
                limits["like"] = safety["daily_like_limit"]
            if "daily_publish_limit" in safety:
                limits["publish"] = safety["daily_publish_limit"]
            if "daily_favorite_limit" in safety:
                limits["favorite"] = safety["daily_favorite_limit"]
        except Exception:
            pass

    return jsonify({"date": quota_date, "counts": counts, "limits": limits})


# ---- Evolution ------------------------------------------------------------

@app.route("/api/evolution")
def api_evolution():
    """Read evolution.json knowledge base."""
    fpath = LOGS_DIR / "evolution.json"
    if not fpath.exists():
        return jsonify({"winning_patterns": [], "losing_patterns": [], "audience_insights": [], "trending_topics": []})
    try:
        data = json.loads(fpath.read_text(encoding="utf-8"))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e), "winning_patterns": [], "losing_patterns": [], "audience_insights": [], "trending_topics": []})


# ---- Fans Profile ---------------------------------------------------------

@app.route("/api/fans-profile")
def api_fans_profile():
    """Return fans profile data from analytics or mock."""
    # Try to extract from latest analytics file
    analytics_files = sorted(ANALYTICS_DIR.glob("????-??-??.json"), reverse=True)
    for af in analytics_files:
        try:
            data = json.loads(af.read_text(encoding="utf-8"))
            fans = data.get("fans_profile")
            if fans:
                return jsonify(fans)
        except Exception:
            continue

    # Return mock structure
    return jsonify({
        "total": 0,
        "gender": {"male": 50, "female": 50},
        "interests": ["AI工具", "效率提升", "自动化", "工作流", "团队管理"],
    })


# ---- Strategy CRUD --------------------------------------------------------

@app.route("/api/strategy", methods=["GET"])
def api_strategy_get():
    """Read strategy.json."""
    if not STRATEGY_FILE.exists():
        return jsonify({"error": "strategy.json not found"}), 404
    try:
        data = json.loads(STRATEGY_FILE.read_text(encoding="utf-8"))
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/strategy", methods=["POST"])
def api_strategy_update():
    """Update strategy.json."""
    body = request.get_json(force=True)
    if not body:
        return jsonify({"error": "JSON body required"}), 400

    required_keys = {"account", "persona", "content_strategy", "schedule", "safety", "daemon"}
    missing = required_keys - set(body.keys())
    if missing:
        return jsonify({"error": f"Missing required keys: {', '.join(missing)}"}), 400

    try:
        with open(STRATEGY_FILE, "w", encoding="utf-8") as f:
            json.dump(body, f, ensure_ascii=False, indent=2)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ---- Daemon Control -------------------------------------------------------

@app.route("/api/daemon/start", methods=["POST"])
def api_daemon_start():
    """Start the daemon process."""
    daemon_py = WORKSPACE / "daemon.py"
    try:
        env = {**os.environ,
               "http_proxy": "http://127.0.0.1:7890",
               "https_proxy": "http://127.0.0.1:7890",
               "all_proxy": "socks5://127.0.0.1:7890"}
        subprocess.Popen(
            ["python", str(daemon_py), "start"],
            cwd=str(WORKSPACE),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return jsonify({"success": True, "message": "Daemon start command issued"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/daemon/stop", methods=["POST"])
def api_daemon_stop():
    """Stop the daemon process."""
    daemon_py = WORKSPACE / "daemon.py"
    try:
        result = subprocess.run(
            ["python", str(daemon_py), "stop"],
            cwd=str(WORKSPACE),
            capture_output=True,
            text=True,
            timeout=30,
        )
        msg = result.stdout.strip() or result.stderr.strip() or "Daemon stop command issued"
        return jsonify({"success": True, "message": msg})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ---- Accounts -------------------------------------------------------------

@app.route("/api/accounts")
def api_accounts():
    """List accounts via CLI, cached for 60s."""
    now = time.time()
    if _accounts_cache["data"] is not None and (now - _accounts_cache["ts"]) < ACCOUNTS_CACHE_TTL:
        return jsonify(_accounts_cache["data"])

    try:
        result = subprocess.run(
            ["python", str(CLI_PATH), "list-accounts"],
            cwd=str(SKILL_DIR),
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout.strip()
        try:
            data = json.loads(output)
        except json.JSONDecodeError:
            data = {"accounts": [], "raw": output}

        _accounts_cache["ts"] = now
        _accounts_cache["data"] = data
        return jsonify(data)
    except subprocess.TimeoutExpired:
        return jsonify({"accounts": [], "error": "list-accounts timed out"})
    except Exception as e:
        return jsonify({"accounts": [], "error": str(e)})


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Ensure directories exist
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
    PUBLISHED_DIR.mkdir(parents=True, exist_ok=True)
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    CONTENT_CAL_DIR.mkdir(parents=True, exist_ok=True)

    # Reconcile stale tasks
    _reconcile_running_tasks()

    print(f"XHS Dashboard server starting on port 5800...")
    print(f"Workspace: {WORKSPACE}")
    app.run(host="0.0.0.0", port=5800, debug=False)
