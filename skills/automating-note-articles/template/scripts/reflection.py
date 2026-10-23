"""振り返り（reflection）の記録。

保存先は手元の SQLite（.claude/db/agents.db）。sqlite3 コマンドは要らない。

  python scripts/reflection.py start --slug media-writer [--parent 12] [--trigger subagent]
      → 新しい行を作り、番号（RUN_ID）を出す
  python scripts/reflection.py finish 13 @work/reflection_13.json
      → 4層の振り返りを書いて完了にする。JSON のキー:
        what_done / quality_check / quality_score(0-100) / self_improvement / content_improvement / result_full
        / items_processed / items_succeeded / items_failed（どれも省略可）
  python scripts/reflection.py fail 13 "理由"
  python scripts/reflection.py recent media-editor [--hours 24]
      → 直近に完了した自分の実行（重複して動かないための確認。実行中の行は数えない）
  python scripts/reflection.py lessons media-writer
      → 直近3回の self_improvement / content_improvement（前回の反省を読む）
  python scripts/reflection.py status 13
      → その実行の状態（running / completed / error）。run-agent.ps1 が最後まで終えたかを見る
"""
import json
import sqlite3
import sys

from _env import ROOT

DB = ROOT / ".claude" / "db" / "agents.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS reflections (
  id                  INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_slug          TEXT NOT NULL,
  parent_run_id       INTEGER,
  trigger             TEXT,
  status              TEXT DEFAULT 'running',
  items_processed     INTEGER DEFAULT 0,
  items_succeeded     INTEGER DEFAULT 0,
  items_failed        INTEGER DEFAULT 0,
  started_at          TEXT DEFAULT (datetime('now','localtime')),
  ended_at            TEXT,
  quality_score       INTEGER,
  what_done           TEXT,
  quality_check       TEXT,
  self_improvement    TEXT,
  content_improvement TEXT,
  result_full         TEXT,
  error_message       TEXT
);
"""

FIELDS = ("what_done", "quality_check", "quality_score", "self_improvement", "content_improvement",
          "result_full", "items_processed", "items_succeeded", "items_failed")


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def _opt(args, name, default=None):
    return args[args.index(name) + 1] if name in args else default


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd, args = argv[1], argv[2:]
    con = connect()

    if cmd == "start":
        parent = _opt(args, "--parent")
        cur = con.execute(
            "INSERT INTO reflections (agent_slug, parent_run_id, trigger) VALUES (?, ?, ?)",
            (_opt(args, "--slug"), int(parent) if parent and parent != "0" else None, _opt(args, "--trigger", "manual")),
        )
        con.commit()
        print(cur.lastrowid)
    elif cmd == "finish":
        run_id, src = int(args[0]), args[1]
        data = json.loads((ROOT / src[1:]).read_text(encoding="utf-8") if src.startswith("@") else src)
        values = {k: data[k] for k in FIELDS if k in data}
        for k, v in values.items():
            if isinstance(v, (list, dict)):
                values[k] = json.dumps(v, ensure_ascii=False)
        sets = ", ".join(f"{k} = ?" for k in values)
        con.execute(
            f"UPDATE reflections SET {sets}{', ' if sets else ''}status='completed', ended_at=datetime('now','localtime') WHERE id=?",
            (*values.values(), run_id),
        )
        con.commit()
        print(f"reflection {run_id} completed")
    elif cmd == "fail":
        con.execute("UPDATE reflections SET status='error', error_message=?, ended_at=datetime('now','localtime') WHERE id=?",
                    (args[1], int(args[0])))
        con.commit()
    elif cmd == "recent":
        hours = int(_opt(args, "--hours", 24))
        rows = con.execute(
            "SELECT id, status, items_processed, items_succeeded, items_failed, started_at FROM reflections "
            "WHERE agent_slug=? AND status='completed' AND started_at > datetime('now','localtime', ?) ORDER BY id",
            (args[0], f"-{hours} hours"),
        ).fetchall()
        print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
    elif cmd == "lessons":
        rows = con.execute(
            "SELECT id, quality_score, self_improvement, content_improvement FROM reflections "
            "WHERE agent_slug=? AND quality_score IS NOT NULL ORDER BY id DESC LIMIT 3",
            (args[0],),
        ).fetchall()
        print(json.dumps([dict(r) for r in rows], ensure_ascii=False, indent=2))
    elif cmd == "status":
        row = con.execute("SELECT status FROM reflections WHERE id=?", (int(args[0]),)).fetchone()
        print(row["status"] if row else "missing")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
