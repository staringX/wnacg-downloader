"""読み取り専用 HTTP API のスナップショット（Tier B）

起動中のバックエンドの GET 系エンドポイント応答を保存/比較する。
クローラ移行は読み取り API を変えないため、移行前後で完全一致するはずという前提の安全網。

使い方（backend で）:
    # 移行前にベースラインを保存
    .venv/bin/python scripts/snapshot_api.py capture
    # 移行後に比較（差分があれば終了コード 1）
    .venv/bin/python scripts/snapshot_api.py compare

環境変数 API_BASE で対象を指定（既定 http://localhost:18000）。
sync/download など副作用・非同期のエンドポイントは対象外（Tier A と E2E スモークで担保）。
"""
import os
import sys
import json
import difflib
import urllib.request

API_BASE = os.environ.get("API_BASE", "http://localhost:18000")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP_DIR = os.path.join(ROOT, "tests", "api_snapshots")

# 読み取り専用・決定的なエンドポイント
ENDPOINTS = [
    ("health", "/health"),
    ("root", "/"),
    ("mangas", "/api/mangas"),
    ("recent_updates", "/api/recent-updates"),
    ("settings", "/api/settings"),
    ("download_queue", "/api/download/queue"),
    ("tasks", "/api/tasks?limit=20"),
]

# 比較時に無視する揮発フィールド（移行と無関係に変動しうる値）
VOLATILE_KEYS = {"created_at", "updated_at", "updated_at_db", "completed_at",
                 "downloaded_at", "timestamp"}


def fetch(path):
    url = f"{API_BASE}{path}"
    with urllib.request.urlopen(url, timeout=20) as r:
        return json.loads(r.read().decode("utf-8"))


def normalize(obj):
    """揮発フィールドをマスクし、リストは安定ソート"""
    if isinstance(obj, dict):
        return {k: ("<volatile>" if k in VOLATILE_KEYS else normalize(v))
                for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        items = [normalize(x) for x in obj]
        # id があれば id で安定ソート
        try:
            items.sort(key=lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False))
        except Exception:
            pass
        return items
    return obj


def dumps(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)


def cmd_capture():
    os.makedirs(SNAP_DIR, exist_ok=True)
    for name, path in ENDPOINTS:
        try:
            data = normalize(fetch(path))
            with open(os.path.join(SNAP_DIR, f"{name}.json"), "w", encoding="utf-8") as f:
                f.write(dumps(data))
            print(f"  capture: {name} ({path})")
        except Exception as e:
            print(f"  SKIP {name} ({path}): {type(e).__name__} {e}")
    print(f"保存先: {SNAP_DIR}")


def cmd_compare():
    if not os.path.isdir(SNAP_DIR):
        print("ベースライン未保存。先に capture を実行してください。")
        sys.exit(2)
    diffs = 0
    for name, path in ENDPOINTS:
        base_file = os.path.join(SNAP_DIR, f"{name}.json")
        if not os.path.exists(base_file):
            continue
        old = open(base_file, encoding="utf-8").read()
        try:
            new = dumps(normalize(fetch(path)))
        except Exception as e:
            print(f"  ERROR {name}: {e}")
            diffs += 1
            continue
        if old == new:
            print(f"  OK   {name}")
        else:
            diffs += 1
            print(f"  DIFF {name} ({path}):")
            for line in difflib.unified_diff(old.splitlines(), new.splitlines(),
                                             "baseline", "current", lineterm=""):
                print("    " + line)
    if diffs:
        print(f"\n差分あり: {diffs} エンドポイント")
        sys.exit(1)
    print("\n全エンドポイント一致")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "capture"
    print(f"API_BASE = {API_BASE} / mode = {cmd}")
    if cmd == "capture":
        cmd_capture()
    elif cmd == "compare":
        cmd_compare()
    else:
        print("usage: snapshot_api.py [capture|compare]")
        sys.exit(2)
