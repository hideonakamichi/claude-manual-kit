"""共通: .env.local（秘密のキー）と media.config.json（案件ごとの値）を読む。

どのスクリプトも最初に `from _env import ROOT, env, CONFIG` で使う。
.env.local には秘密のキーが入るので、画面やログに値を出さない。
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Windows の画面でも日本語が化けないようにする
for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


_load_env_file(ROOT / ".env.local")

CONFIG = json.loads((ROOT / "media.config.json").read_text(encoding="utf-8"))

# 画像の作り方: "manual"＝指示文だけ作り、人が ChatGPT・Canva などで画像にする（無料）／"gemini"＝Gemini で自動（支払いの登録が要る）
IMAGE_MODE = CONFIG.get("image_mode", "manual")

# 記事のテイスト。話者ありの2つは **名前**: の発言で書き、ほかは地の文で書く
STYLES = {
    "dialogue": "2人の対話", "interview": "インタビュー風",
    "essay": "読み物", "story": "ストーリー＋解説", "howto": "ノウハウ・まとめ", "documentary": "ドキュメンタリー・密着",
}
SPEAKER_STYLES = ("dialogue", "interview")
MEMO_STYLES = ("interview", "documentary")  # 本人の取材メモが無いと書けない（発言・場面を作らないため）
STYLE = CONFIG.get("article_style", "dialogue")          # 既定（テイストが空の記事はこれで書く）
ALLOWED_STYLES = CONFIG.get("styles", [STYLE])            # この案件で使ってよいテイスト（編集長はこの中からすすめる）
for _s in [STYLE, *ALLOWED_STYLES]:
    if _s not in STYLES:
        sys.exit(f"[env] ERROR: media.config.json の article_style / styles は {' / '.join(STYLES)} のどれか（いま: {_s}）")


def style_of(row: dict) -> str:
    """記事1本のテイスト。DB の style が空なら既定"""
    return row.get("style") or STYLE


def env(name: str, default: str | None = None, required: bool = False) -> str | None:
    value = os.environ.get(name, default)
    if required and not value:
        sys.exit(f"[env] ERROR: .env.local に {name} を設定してください（.env.local.sample を参照）")
    return value
