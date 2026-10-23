"""合格した記事を、note に貼る下書きとして書き出す。画像を入れたあとにもう一度動かすと、画像入りの下書きになる。

  python scripts/export_note.py 5
  python scripts/export_note.py 5 --open    # 書き出して、下書き.html をブラウザで開く（画像が足りなければ置き場所のフォルダも）
  python scripts/export_note.py --file work/article_5.md "タイトル"   # DB を使わず試す（番号は test）

できるもの（note下書き/{id}/）:
  下書き.html   … ブラウザで開き、①から順にボタンでコピー → note で Ctrl+V。文章と図解を順番に貼る
                  （note は文章と画像をまとめて貼ると全部消すため。試して確認した）
  images/       … 画像の置き場所。00_見出し画像.png / 01_図解.png … の名前で入れる（.jpg .jpeg .webp も可）
                  image_mode が manual なら、画像を作る指示文（*_指示文.txt）もここに出る
  タイトル.txt

画像の探し順: note下書き/{id}/images/{決まった名前} → images/{id}-{name}.png（gemini で作ったもの）
"""
import base64
import html
import mimetypes
import os
import re
import shutil
import sys

from _env import ROOT

OUT = ROOT / "note下書き"
EXTS = (".png", ".jpg", ".jpeg", ".webp")


def inline(text: str) -> str:
    """太字とリンクだけを HTML にする（それ以外の記号はそのまま文字として出す）"""
    out = html.escape(text, quote=False)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', out)
    return out


def data_uri(path) -> str:
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def is_image(path) -> bool:
    """中身が本当に画像か（ブラウザの「ページを保存」だと、名前が .png でも中身は Web ページになる）"""
    head = path.read_bytes()[:12]
    return head.startswith((b"\x89PNG", b"\xff\xd8\xff")) or (head[:4] == b"RIFF" and head[8:12] == b"WEBP")


def find_image(folder, stem: str, rel: str):
    """人が入れた画像（決まった名前）→ gemini で作った画像 の順に探す"""
    for ext in EXTS:
        # 「01_図解.png.png」も拾う（Windows が拡張子を隠していると、名前に .png を打ち足して二重になる）
        for p in (folder / "images" / f"{stem}{ext}", folder / "images" / f"{stem}{ext}{ext}"):
            if not p.is_file():
                continue
            if is_image(p):
                return p
            print(f"[export] {p.name} は画像ではありません（Web ページを保存した形）。"
                  "画像を右クリック →「名前を付けて画像を保存」か、ダウンロードのボタンで保存し直す", file=sys.stderr)
    generated = ROOT / rel
    if generated.is_file():
        dest = folder / "images" / f"{stem}.png"
        shutil.copy(generated, dest)
        return dest
    return None


def to_segments(md: str, images: dict) -> list:
    """記事を「文章のかたまり」と「図解」に分ける。note は文章と画像をまとめて貼ると全部消すため、順番に1つずつ貼る"""
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    segments, parts, box = [], [], None

    def flush():
        if parts:
            segments.append(("text", "\n".join(parts)))
            parts.clear()

    for raw in md.split("\n"):
        s = raw.strip()
        if box is not None:
            if s == ":::":
                kind, title, items = box
                if kind == "steps":
                    parts.append("<ol>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ol>")
                else:
                    body = "<br>".join(inline(i) for i in items)
                    parts.append(f"<blockquote><strong>{html.escape(title)}</strong><br>{body}</blockquote>")
                box = None
            elif s:
                box[2].append(re.sub(r"^(\d+\.|[-*]) ", "・" if box[0] != "steps" else "", s))
            continue
        if not s:
            continue
        m = re.match(r'^:::(point|caution|steps)(?:\{title="([^"]+)"\})?$', s)
        if m:
            box = (m.group(1), m.group(2) or "", [])
        elif s.startswith("### "):
            parts.append(f"<h3>{inline(s[4:])}</h3>")
        elif s.startswith("## "):
            parts.append(f"<h2>{inline(s[3:])}</h2>")
        elif s.startswith("!["):
            alt, rel = re.match(r"!\[([^\]]*)\]\(([^)]+)\)", s).groups()
            flush()
            stem, path = images.get(rel, ("?", None))
            segments.append(("image", (stem, path, alt)))
        else:
            sp = re.match(r"^\*\*([^*]+)\*\*: (.*)$", s)
            if sp:
                parts.append(f"<p><strong>{html.escape(sp.group(1))}</strong>　{inline(sp.group(2))}</p>")
            else:
                parts.append(f"<p>{inline(s)}</p>")
    flush()
    return segments


def render_steps(segments) -> str:
    """順番に押すボタンと、その中身（見本）を並べる"""
    nums = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"
    out = []
    for i, (kind, val) in enumerate(segments):
        no = nums[i] if i < len(nums) else f"({i + 1})"
        if kind == "text":
            out.append(f'<div class="step"><button class="cp" data-kind="text" data-target="s{i}">{no} 文章をコピー</button>'
                       f'<span class="done"></span><div class="seg" id="s{i}">{val}</div></div>')
        else:
            stem, path, alt = val
            if path:
                out.append(f'<div class="step"><button class="cp" data-kind="image" data-target="s{i}">{no} 図解（{html.escape(stem)}）をコピー</button>'
                           f'<span class="done"></span><div class="seg"><img id="s{i}" src="{data_uri(path)}" alt="{html.escape(alt)}"></div></div>')
            else:
                out.append(f'<div class="step"><span class="missing">{no} {html.escape(stem)} がまだありません（上の「先に画像を作る」）</span></div>')
    return "\n".join(out)


PAGE = """<!doctype html>
<!-- このファイルはブラウザで開く（エクスプローラーでダブルクリック）。VSCode で文字だけが見えているときは、左の一覧でこのファイルを右クリック →「エクスプローラーで表示」→ ダブルクリック。ここに見えているのは、ボタンを動かすためのコード -->
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}｜note 下書き</title>
<style>
body{{margin:0;background:#f4f4f2;color:#222;font:16px/1.9 "Zen Kaku Gothic New","Hiragino Sans",sans-serif}}
.wrap{{max-width:720px;margin:0 auto;padding:24px 16px 80px}}
.howto{{background:#1A365D;color:#fff;border-radius:12px;padding:16px 20px;margin-bottom:24px}}
.howto ol{{margin:8px 0 0;padding-left:1.4em}} .howto code{{background:rgba(255,255,255,.15);padding:0 4px;border-radius:4px}}
.howto button{{margin-top:12px;font:inherit;font-weight:700;background:#DD6B20;color:#fff;border:0;border-radius:8px;padding:10px 18px;cursor:pointer}}
.howto .copied{{margin-left:10px}} .copyline{{background:#fff;border:1px solid #ccc;border-radius:6px;padding:2px 8px;color:#222}}
.todo{{background:#fff;border:2px dashed #DD6B20;border-radius:12px;padding:16px 20px;margin-bottom:24px}}
.todo pre{{white-space:pre-wrap;background:#f7f7f5;border-radius:8px;padding:10px 12px;font:14px/1.7 inherit}}
.todo button{{font:inherit;font-size:14px;background:#1A365D;color:#fff;border:0;border-radius:6px;padding:6px 12px;cursor:pointer}}
.todo .name{{font-weight:700;color:#DD6B20}}
article{{background:transparent}}
h1{{font-size:24px;line-height:1.5}} h2{{font-size:20px;margin-top:2em;border-bottom:2px solid #234386}}
blockquote{{margin:1em 0;padding:12px 16px;border-left:4px solid #234386;background:#f0f3f9}}
figure{{margin:1em 0}} img{{max-width:100%;border-radius:8px}} .missing{{color:#DD6B20;font-weight:700}}
.eyecatch img{{width:100%}}
.step{{border:1px solid #ddd;border-radius:10px;padding:12px 14px;margin:12px 0;background:#fff}}
.step.used{{opacity:.55}} .step.now{{opacity:1;border:2px solid #DD6B20}}
.cp{{font:inherit;font-weight:700;background:#DD6B20;color:#fff;border:0;border-radius:8px;padding:8px 14px;cursor:pointer}}
.done{{margin-left:10px;font-weight:700;color:#1A365D}} .seg{{margin-top:8px}} .note{{font-size:14px;opacity:.85}}
</style></head><body><div class="wrap">
{todo}
<div class="howto"><strong>note への貼り方</strong>
<ol>
<li>note で「投稿 → テキスト」を開き、タイトルを貼る: <span class="copyline" id="ttl">{title}</span> <button class="copyprompt" data-target="ttl">タイトルをコピー</button></li>
<li>見出し画像: note の画像のボタンから <code>{eyecatch_path}</code> を選ぶ</li>
<li>本文の欄（タイトルの下）をクリックする</li>
<li>下のボタンを <strong>①から順に</strong> 押し、押すたびに note で <strong>Ctrl + V</strong>。クリックし直さなくてよい</li>
<li><strong>図解を貼ったあとは Enter を1回</strong>（押さないと、次の文章が画像の説明欄＝キャプションに入ってしまう）</li>
<li>公開したら: <code>python scripts/topics.py posted {id} 公開したURL</code></li>
</ol>
<p class="note">文章と画像をまとめて貼ると、note は全部消してしまう。だから順番に1つずつ貼る。ボタンが効かないときは、文章はなぞって Ctrl+C、図解は右クリック →「画像をコピー」。</p>
</div>
<div class="eyecatch">{eyecatch_img}</div>
<h1>{title}</h1>
<article id="body">
{body}
</article></div>
<script>
async function copyImage(img) {{
  var c = document.createElement('canvas'); c.width = img.naturalWidth; c.height = img.naturalHeight;
  c.getContext('2d').drawImage(img, 0, 0);
  var blob = await new Promise(function (r) {{ c.toBlob(r, 'image/png'); }});
  await navigator.clipboard.write([new ClipboardItem({{'image/png': blob}})]);
}}
function copyText(el) {{
  var r = document.createRange(); r.selectNodeContents(el);
  var s = window.getSelection(); s.removeAllRanges(); s.addRange(r);
  var ok = false; try {{ ok = document.execCommand('copy'); }} catch (e) {{}}
  s.removeAllRanges(); if (!ok) throw new Error('copy');
}}
document.querySelectorAll('.cp').forEach(function (b) {{
  b.addEventListener('click', async function () {{
    var el = document.getElementById(b.dataset.target), msg = b.nextElementSibling;
    try {{
      if (b.dataset.kind === 'image') await copyImage(el); else copyText(el);
      document.querySelectorAll('.step').forEach(function (s) {{ s.classList.remove('now'); }});
      b.parentElement.classList.add('now', 'used'); msg.textContent = b.dataset.kind === 'image' ? 'コピーしました → note で Ctrl + V → Enter' : 'コピーしました → note で Ctrl + V';
    }} catch (e) {{ msg.textContent = 'コピーできませんでした（' + (b.dataset.kind === 'image' ? '右クリック →「画像をコピー」' : 'なぞって Ctrl+C') + '）'; }}
  }});
}});
document.querySelectorAll('.copyprompt').forEach(function (b) {{
  b.addEventListener('click', function () {{
    try {{ copyText(document.getElementById(b.dataset.target)); b.textContent = 'コピーしました'; }}
    catch (e) {{ b.textContent = '選んで Ctrl+C'; }}
  }});
}});
</script></body></html>
"""


def export(article_id, title: str, md: str):
    folder = OUT / str(article_id)
    (folder / "images").mkdir(parents=True, exist_ok=True)

    eyecatch = re.findall(r"<!-- EYECATCH (\S+) -->", md)
    figs = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", md)
    images, todo = {}, []
    for n, rel in enumerate(eyecatch + figs):
        stem = "00_見出し画像" if n == 0 and eyecatch else f"{n:02d}_図解"
        path = find_image(folder, stem, rel)
        images[rel] = (stem, path)
        prompt_file = (ROOT / rel).with_suffix(".prompt.txt")
        if not path and prompt_file.is_file():
            aspect, _, prompt = prompt_file.read_text(encoding="utf-8").partition("\n")
            shutil.copy(prompt_file, folder / "images" / f"{stem}_指示文.txt")
            todo.append(
                f'<p><span class="name">{html.escape(stem)}.png</span>（{html.escape(aspect.replace("aspect:", "縦横比").strip())}）</p>'
                f'<pre id="p{n}">{html.escape(prompt.strip())}</pre>'
                f'<button class="copyprompt" data-target="p{n}">指示文をコピー</button>')
        elif not path:
            print(f"[export] 画像も指示文もありません: {rel}", file=sys.stderr)

    todo_html = ""
    if todo:
        todo_html = ('<div class="todo"><strong>先に画像を作る（あと {n} 枚）</strong>'
                     '<ol><li>指示文をコピーして ChatGPT・Canva などに貼り、画像を作る</li>'
                     '<li>できた画像を、オレンジの名前に変えて次のフォルダに入れる<br><code id="imgdir">{folder}</code> '
                     '<button class="copyprompt" data-target="imgdir">場所をコピー</button>（保存の画面の上の場所の欄に貼って Enter）<br>'
                     '保存は画像を右クリック →「名前を付けて画像を保存」かダウンロードのボタン（Ctrl+S のページ保存は Web ページになって使えない）。'
                     '名前に .png が見えていなければ、.png は打たない（二重になる）</li>'
                     '<li>入れ終わったら、Claude に「{id} の下書きを作り直して」（または <code>python scripts/export_note.py {id}</code>）。図解のボタンが出る</li></ol>'
                     ).format(n=len(todo), folder=html.escape(str(folder / "images")), id=article_id) + "".join(todo) + "</div>"

    ey_stem, ey_path = images.get(eyecatch[0], ("", None)) if eyecatch else ("", None)
    eyecatch_img = f'<img src="{data_uri(ey_path)}" alt="見出し画像">' if ey_path else ""
    eyecatch_path = str(ey_path) if ey_path else f"images\\{ey_stem}.png（まだありません）" if ey_stem else "（なし）"
    page = PAGE.format(title=html.escape(title), id=article_id, body=render_steps(to_segments(md, images)), todo=todo_html,
                       eyecatch_path=html.escape(eyecatch_path), eyecatch_img=eyecatch_img)
    (folder / "下書き.html").write_text(page, encoding="utf-8")
    (folder / "タイトル.txt").write_text(title + "\n", encoding="utf-8")
    missing = sum(1 for _, p in images.values() if not p)
    print(f"{folder}（画像 {len(images) - missing}/{len(images)} 枚）")
    print(f"  下書き（ブラウザで開く）: {(folder / '下書き.html').as_uri()}")
    print(f"  画像の置き場所: {(folder / 'images').as_uri()}")
    return folder, missing


def open_draft(folder, missing: int):
    """下書き.html をいつものブラウザで開く。画像が足りなければ、置き場所のフォルダも開く（人がチャットで動かすときだけ使う）"""
    os.startfile(folder / "下書き.html")
    if missing:
        os.startfile(folder / "images")


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    want_open = "--open" in argv
    argv = [a for a in argv if a != "--open"]
    if argv[1] == "--file":
        folder, missing = export("test", argv[3], (ROOT / argv[2]).read_text(encoding="utf-8"))
    else:
        from db import get_article, update
        row = get_article(int(argv[1]))
        if row["status"] not in ("approved", "posted"):
            sys.exit(f"[export] 記事 {row['id']} は合格していません（status={row['status']}）")
        folder, missing = export(row["id"], row["article_title"], row["article_md"])
        update(row["id"], {"export_dir": str(folder)})
    if want_open:
        open_draft(folder, missing)


if __name__ == "__main__":
    main(sys.argv)
