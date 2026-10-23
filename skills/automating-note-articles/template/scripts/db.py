"""Cloudflare D1（記事の保存先 DB）を API で操作する。

  python scripts/db.py init                         # DB が無ければ作り、表を作る（最初の1回）
  python scripts/db.py list [queued]                # 一覧（状態で絞れる）
  python scripts/db.py next 1                       # 書く待ち（queued）を古い順に
  python scripts/db.py topics                       # これまでのネタ全部（重なり確認）
  python scripts/db.py get 5                        # 1本の記事を全部見る
  python scripts/db.py add-ideas work/ideas.json    # ネタ候補をまとめて入れる
  python scripts/db.py set 5 status=approved retry_count=1   # 項目を書き換える（状態を変えるのは編集長だけ）
  python scripts/db.py save-draft 5 work/article_5.md "タイトル" work/notes_5.json
  python scripts/db.py add-review 5 work/review_5.json      # レビュー結果を review_log に足す
  python scripts/db.py sql "SELECT count(*) AS n FROM articles WHERE status='idea'"   # 読むだけの SQL
"""
import json
import re
import sys
import urllib.error
import urllib.request

from _env import ALLOWED_STYLES, CONFIG, ROOT, STYLE, env, style_of

API = "https://api.cloudflare.com/client/v4"
JSON_COLS = ("products", "research_notes", "review_log")
_db_id = None


def _call(method: str, path: str, body=None):
    token = env("CLOUDFLARE_API_TOKEN", required=True)
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(f"{API}{path}", data=data, method=method,
                                 headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            return json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"[db] ERROR {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")


def _account():
    return env("CLOUDFLARE_ACCOUNT_ID", required=True)


def _name():
    return env("D1_DATABASE_NAME") or CONFIG["d1_database"]


def database_id(create: bool = False) -> str:
    """DB の名前から ID を探す（.env.local に ID を書かなくてよいように）"""
    global _db_id
    if _db_id:
        return _db_id
    found = [d for d in _call("GET", f"/accounts/{_account()}/d1/database?name={_name()}")["result"] if d["name"] == _name()]
    if found:
        _db_id = found[0]["uuid"]
    elif create:
        _db_id = _call("POST", f"/accounts/{_account()}/d1/database", {"name": _name()})["result"]["uuid"]
        print(f"[db] DB「{_name()}」を作りました", file=sys.stderr)
    else:
        sys.exit(f"[db] ERROR: DB「{_name()}」がありません。先に python scripts/db.py init")
    return _db_id


def query(sql: str, params=()) -> list[dict]:
    res = _call("POST", f"/accounts/{_account()}/d1/database/{database_id()}/query",
                {"sql": sql, "params": list(params)})
    rows = res["result"][0]["results"]
    for row in rows:
        for col in JSON_COLS:
            if isinstance(row.get(col), str):
                row[col] = json.loads(row[col])
    return rows


def update(article_id: int, body: dict) -> list[dict]:
    values = {k: json.dumps(v, ensure_ascii=False) if k in JSON_COLS else v for k, v in body.items()}
    sets = ", ".join(f"{k} = ?" for k in values)
    return query(f"UPDATE articles SET {sets}, updated_at = datetime('now') WHERE id = ? RETURNING *",
                 (*values.values(), article_id))


def get_article(article_id: int) -> dict:
    rows = query("SELECT * FROM articles WHERE id = ?", (article_id,))
    if not rows:
        sys.exit(f"[db] ERROR: 記事 {article_id} が見つかりません")
    return rows[0]


def init():
    database_id(create=True)
    schema = (ROOT / "d1" / "schema.sql").read_text(encoding="utf-8")
    schema = re.sub(r"--[^\n]*", "", schema)
    for stmt in [s.strip() for s in schema.split(";") if s.strip()]:
        query(stmt)
    # 前のキットで作った DB に、あとから足した欄を足す（もう一度 init すればよい）
    have = {r["name"] for r in query("PRAGMA table_info(articles)")}
    for col in ("style", "style_reason"):
        if col not in have:
            query(f"ALTER TABLE articles ADD COLUMN {col} TEXT")
            print(f"[db] 欄「{col}」を足しました", file=sys.stderr)
    return [{"database": _name(), "tables": [r["name"] for r in query("SELECT name FROM sqlite_master WHERE type='table'")]}]


def _file(path: str) -> str:
    return (ROOT / path.lstrip("@")).read_text(encoding="utf-8")


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd, args = argv[1], argv[2:]

    if cmd == "init":
        out = init()
    elif cmd == "list":
        where, params = ("WHERE status = ?", (args[0],)) if args else ("", ())
        out = query(f"SELECT id, status, topic, angle, products, style, article_title, retry_count, note_url FROM articles {where} ORDER BY id", params)
    elif cmd == "next":
        out = query("SELECT id, topic, angle, products, style FROM articles WHERE status = 'queued' ORDER BY id LIMIT ?",
                    (int(args[0]) if args else 1,))
        for r in out:
            r["style"] = style_of(r)
    elif cmd == "topics":
        out = query("SELECT id, status, topic FROM articles ORDER BY id")
    elif cmd == "get":
        out = get_article(int(args[0]))
    elif cmd == "add-ideas":
        out = []
        for idea in json.loads(_file(args[0])):
            style = idea.get("style") or STYLE
            if style not in ALLOWED_STYLES:
                sys.exit(f"[db] ERROR: 「{idea['topic']}」の style {style} は、この案件で使えるテイスト（{' / '.join(ALLOWED_STYLES)}）に無い")
            out += query("INSERT INTO articles (topic, angle, products, style, style_reason) VALUES (?, ?, ?, ?, ?) RETURNING id, topic, style",
                         (idea["topic"], idea.get("angle", ""), json.dumps(idea.get("products", []), ensure_ascii=False),
                          style, idea.get("style_reason", "")))
    elif cmd == "set":
        body = {}
        for pair in args[1:]:
            key, value = pair.split("=", 1)
            body[key] = int(value) if value.isdigit() else (None if value == "null" else value)
        out = [{"id": r["id"], **{k: r[k] for k in body}} for r in update(int(args[0]), body)]
    elif cmd == "save-draft":
        article_id, md_file, title, notes_file = int(args[0]), args[1], args[2], args[3]
        rows = update(article_id, {"article_md": _file(md_file), "article_title": title,
                                   "research_notes": json.loads(_file(notes_file))})
        out = [{"id": r["id"], "article_title": r["article_title"], "chars": len(r["article_md"] or "")} for r in rows]
    elif cmd == "add-review":
        log = get_article(int(args[0])).get("review_log") or []
        log.append(json.loads(_file(args[1])))
        out = [{"id": r["id"], "reviews": len(r["review_log"])} for r in update(int(args[0]), {"review_log": log})]
    elif cmd == "sql":
        if not re.match(r"^\s*SELECT\b", args[0], re.I):
            sys.exit("[db] sql は読むだけ（SELECT）。書き換えは set / save-draft / add-review / add-ideas を使う")
        out = query(args[0], args[1:])
    else:
        sys.exit(__doc__)

    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main(sys.argv)
