"""見出し画像・図解を用意する。media.config.json の image_mode で動きが変わる。

  gemini … Gemini で画像を作り images/{id}-{name}.png に保存（支払いの登録が要る）
  manual … 画像は作らず、指示文を images/{id}-{name}.prompt.txt に保存。人が ChatGPT・Canva などで画像にする（無料）
どちらでも、記事に書くパスは images/{id}-{name}.png（人が作った画像もこの名前で置けば下書きに入る）。

  python scripts/gen_image.py 5 eyecatch "プロンプト" --aspect 16:9
  python scripts/gen_image.py 5 fig1 "プロンプト" --aspect 4:3

できたら記事に書くパス（例: images/5-fig1.png）を1行で出す。作れなければ止まる。
"""
import base64
import json
import sys
import urllib.error
import urllib.request

from _env import IMAGE_MODE, ROOT, env


def generate(prompt: str, aspect: str) -> bytes:
    key = env("GEMINI_API_KEY", required=True)
    model = env("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-image-preview")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"], "imageConfig": {"aspectRatio": aspect}},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=180) as res:
            data = json.loads(res.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        sys.exit(f"[gen_image] Gemini ERROR {e.code}: {e.read().decode('utf-8', 'replace')[:500]}")
    for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
        inline = part.get("inlineData") or part.get("inline_data")
        if inline:
            return base64.b64decode(inline["data"])
    sys.exit(f"[gen_image] 画像が返ってきませんでした: {json.dumps(data, ensure_ascii=False)[:500]}")


def main(argv):
    if len(argv) < 4:
        sys.exit(__doc__)
    article_id, name, prompt = argv[1], argv[2], argv[3]
    aspect = argv[argv.index("--aspect") + 1] if "--aspect" in argv else "16:9"

    rel = f"images/{article_id}-{name}.png"
    (ROOT / "images").mkdir(exist_ok=True)
    if IMAGE_MODE == "manual":
        (ROOT / rel).with_suffix(".prompt.txt").write_text(f"aspect: {aspect}\n{prompt}\n", encoding="utf-8")
    else:
        (ROOT / rel).write_bytes(generate(prompt, aspect))
    print(rel)


if __name__ == "__main__":
    main(sys.argv)
