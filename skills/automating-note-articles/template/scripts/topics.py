"""人が使う操作: ネタを選ぶ・公開済みにする・いまの状態を見る。

  python scripts/topics.py list              # 全部の状態を一覧
  python scripts/topics.py adopt 3 5 7       # 候補(idea)のうち 3,5,7 を採用 → queued（テイストは編集長のすすめのまま）
  python scripts/topics.py style 3 essay     # 記事3のテイストを変える（候補・書く待ちのときだけ）
  python scripts/topics.py drop 4 6          # 候補を不採用 → dropped
  python scripts/topics.py posted 5 https://note.com/xxx/n/yyy   # note に公開した（URL を間違えたら、もう一度実行すれば直る）
  python scripts/topics.py requeue 8         # skipped を書き直し待ちに戻す
"""
import sys

from _env import ALLOWED_STYLES, STYLES, style_of
from db import query

LABEL = {
    "idea": "候補", "queued": "書く待ち", "approved": "合格・note待ち",
    "skipped": "見送り", "posted": "公開済み", "dropped": "不採用",
}


def _set_status(ids, frm, to, extra="", extra_params=()):
    ids = [int(i) for i in ids]
    marks = ",".join("?" for _ in ids)
    rows = query(f"UPDATE articles SET status = ?{extra}, updated_at = datetime('now') "
                 f"WHERE id IN ({marks}) AND status = ? RETURNING id", (to, *extra_params, *ids, frm))
    done = {r["id"] for r in rows}
    for i in ids:
        print(f"  {i}: " + ("OK" if i in done else f"変更なし（{LABEL[frm]}ではない）"))


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd, args = argv[1], argv[2:]

    if cmd == "list":
        rows = query("SELECT id, status, topic, style, style_reason, article_title, note_url FROM articles ORDER BY id")
        for status, label in LABEL.items():
            group = [r for r in rows if r["status"] == status]
            if group:
                print(f"\n■ {label}（{len(group)}）")
                for r in group:
                    print(f"  {r['id']:>3}  [{STYLES[style_of(r)]}] {r['article_title'] or r['topic']}" + (f"  {r['note_url']}" if r["note_url"] else ""))
                    if status in ("idea", "queued") and r["style_reason"]:
                        print(f"       └ {r['style_reason']}")
        print(f"\nテイストを変える: python scripts/topics.py style 番号 テイスト（{' / '.join(ALLOWED_STYLES)}）")
    elif cmd == "adopt":
        _set_status(args, "idea", "queued")
    elif cmd == "drop":
        _set_status(args, "idea", "dropped")
    elif cmd == "posted":
        args[1] = args[1].split("?")[0]  # 共有ボタンの URL に付く ?app_launch=false などを外す
        rows = query("SELECT status FROM articles WHERE id = ?", (int(args[0]),))
        if rows and rows[0]["status"] == "posted":  # URL の打ち間違いを直す。公開日時は最初のまま
            query("UPDATE articles SET note_url = ?, updated_at = datetime('now') WHERE id = ?", (args[1], int(args[0])))
            print(f"  {args[0]}: URL を直しました")
        else:
            _set_status([args[0]], "approved", "posted", ", note_url = ?, posted_at = datetime('now')", (args[1],))
    elif cmd == "style":
        if args[1] not in ALLOWED_STYLES:
            sys.exit(f"テイストは {' / '.join(f'{s}（{STYLES[s]}）' for s in ALLOWED_STYLES)} のどれか。"
                     "ほかを使うときは media.config.json の styles に足す")
        rows = query("UPDATE articles SET style = ?, style_reason = '本人が選んだ', updated_at = datetime('now') "
                     "WHERE id = ? AND status IN ('idea', 'queued') RETURNING id", (args[1], int(args[0])))
        print(f"  {args[0]}: " + (f"テイストを {STYLES[args[1]]} にしました" if rows else "変更なし（候補・書く待ちではない）"))
    elif cmd == "requeue":
        _set_status(args, "skipped", "queued", ", retry_count = 0, skip_reason = NULL")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
