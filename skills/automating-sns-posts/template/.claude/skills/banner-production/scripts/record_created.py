#!/usr/bin/env python3
"""
record_created.py - 作った投稿の記録を logs/created.jsonl に追記する

同じ節で何度も投稿を作らないための記録。theme-picker がこの記録を読む。
1投稿1行の JSON で追記専用。日時は ISO8601（UTC）。
theme は theme-picker が返した値を、一字一句そのまま渡すこと（突合はこの文字列の一致で行う）。

使い方:
  python .claude/skills/banner-production/scripts/record_created.py \
    --theme "..." --output-dir output/YYYY-MM-DD_xxx --slide-count 5

テスト用に別の場所へ書きたいときは --log-file を使う。
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[3]
DEFAULT_LOG = PROJECT_ROOT / "logs" / "created.jsonl"

sys.path.insert(0, str(PROJECT_ROOT / ".claude" / "skills" / "shared" / "scripts"))
from portalock import lock_ex  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--theme", required=True, help="theme-picker が返した theme（そのまま）")
    ap.add_argument("--output-dir", default="", help="生成物の保存先")
    ap.add_argument("--slide-count", type=int, default=None, help="カルーセルの枚数")
    ap.add_argument("--log-file", default=None, help="記録先（省略時は logs/created.jsonl）")
    args = ap.parse_args()

    log = Path(args.log_file) if args.log_file else DEFAULT_LOG
    log.parent.mkdir(parents=True, exist_ok=True)

    entry = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": "banner",
        "theme": args.theme,
        "output_dir": args.output_dir,
    }
    if args.slide_count is not None:
        entry["slide_count"] = args.slide_count

    lock_file = log.parent / ".created.lock"
    with open(lock_file, "w") as lock:
        lock_ex(lock)
        if log.exists():
            for n, line in enumerate(log.read_text(encoding="utf-8").split("\n"), 1):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError:
                    # 切れた行へ追記すると、新しい記録まで読めなくなる。直すまで記録しない
                    print(f"[error] {log} の {n} 行目が JSON として読めません。"
                          "その行を直す（または削除する）まで記録しません", file=sys.stderr)
                    return 1
        needs_newline = log.exists() and log.stat().st_size > 0 and not log.read_bytes().endswith(b"\n")
        with log.open("a", encoding="utf-8") as f:
            if needs_newline:
                f.write("\n")
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"[ok] 記録しました: {log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
