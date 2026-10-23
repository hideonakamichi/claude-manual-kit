"""調べもの用。Jina で Web ページの本文を読む・検索する・URL が生きているか確かめる。

  python scripts/web.py read https://example.go.jp/...         # ページ本文をテキストで
  python scripts/web.py search "〇〇 食べ方"               # 検索（JINA_API_KEY が要る）
  python scripts/web.py status https://...                     # HTTP の番号だけ（200 なら生きている）
  python scripts/web.py key                                    # JINA_API_KEY があるかだけ（値は出さない）

本文は長いので、必要なら --out でファイルに保存して読む:
  python scripts/web.py read https://... --out work/src_1.txt
"""
import sys
import urllib.error
import urllib.parse
import urllib.request

from _env import ROOT, env

UA = "Mozilla/5.0 (owned-media-agent)"


def _get(url: str, headers: dict, timeout=60) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **headers})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.read().decode("utf-8", "replace")


def _auth():
    key = env("JINA_API_KEY")
    return {"Authorization": f"Bearer {key}"} if key else {}


def read(url: str) -> str:
    return _get(f"https://r.jina.ai/{url}", {"Accept": "text/plain", **_auth()})


def search(query: str) -> str:
    if not env("JINA_API_KEY"):
        sys.exit("[web] search には .env.local の JINA_API_KEY が要ります")
    return _get(f"https://s.jina.ai/{urllib.parse.quote(query)}", {"X-Return-Format": "text", **_auth()})


def status(url: str) -> int:
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as res:
                return res.status
        except urllib.error.HTTPError as e:
            if method == "HEAD" and e.code in (403, 405):
                continue  # HEAD を断るサイトは GET で確かめ直す
            return e.code
        except Exception:
            if method == "GET":
                return 0
    return 0


def main(argv):
    if len(argv) == 2 and argv[1] == "key":
        print("JINA_API_KEY: あり" if env("JINA_API_KEY") else "JINA_API_KEY: なし（検索は使えない。ページを読むのは動く）")
        return
    if len(argv) < 3:
        sys.exit(__doc__)
    cmd, arg = argv[1], argv[2]
    out = ROOT / argv[argv.index("--out") + 1] if "--out" in argv else None

    def emit(text):
        if out:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            print(f"{out}（{len(text)}字）")
        else:
            print(text)

    try:
        if cmd == "read":
            emit(read(arg))
        elif cmd == "search":
            emit(search(arg))
        elif cmd == "status":
            print(status(arg))
        else:
            sys.exit(__doc__)
    except urllib.error.HTTPError as e:
        sys.exit(f"[web] ERROR {e.code}: {arg}")


if __name__ == "__main__":
    main(sys.argv)
