"""記事の機械チェック。

  python scripts/check_article.py --id 5          # DB の記事を調べる
  python scripts/check_article.py work/article_5.md   # ファイルを調べる（テイストは記事5の DB の style）
  python scripts/check_article.py work/test.md --style howto   # テイストを指定して調べる

テイストは記事ごと（DB の style）。空なら media.config.json の article_style。

問題が無ければ "OK" と出して終了コード 0。あれば E番号つきで1行ずつ出して終了コード 1。
ルールを足すときは、ライター・レビュアーの SKILL.md にも同じ番号で書く（孤立ルールを作らない）。
"""
import json
import re
import sys

from _env import CONFIG, IMAGE_MODE, MEMO_STYLES, ROOT, SPEAKER_STYLES, STYLE, STYLES, style_of

Q = CONFIG["characters"]["asker"]["name"]      # 質問役（インタビューなら聞き手）
A = CONFIG["characters"]["explainer"]["name"]  # 解説役（インタビューなら話す人）
SPEAKER = re.compile(rf"^\*\*({Q}|{A})\*\*: ")

PRODUCT_URLS = {p["url"] for p in CONFIG["products"]}  # 商品へのリンクはこの URL だけ

AI_PHRASES = ["することができます", "幅広く", "包括的に", "網羅的に", "一助となれば", "について解説します",
              "いかがでしたでしょうか", "いかがでしたか", "まとめると以下", "整理すると", "第一に", "したがって",
              "でございます", "いたします", "ご紹介します"]
# 案件ごとの「言えないこと」（例: 食品なら健康・効能）。media.config.json の forbidden
RISKY = CONFIG["forbidden"]["words"]
RELATIVE_TIME = ["今年", "来年", "去年", "昨年", "今月", "来月", "先月", "最近", "もうすぐ", "今すぐ", "今年度", "昨今"]


def body_chars(md: str) -> int:
    """読者が読む文字の数（記号・URL・コメント・画像を除く）"""
    text = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"^:::.*$", "", text, flags=re.M)
    text = re.sub(r"[#*>\-\s]", "", text)
    return len(text)


def check_article(md: str, style: str = STYLE) -> list[str]:
    TALK = style in SPEAKER_STYLES  # 話者ありのテイスト（対話・インタビュー）か
    errors = []
    lines = md.split("\n")

    # E01: 始まり方（対話＝質問役の質問から／インタビュー＝リード文のあと聞き手の質問から／地の文＝導入文で始めない）/ H1 が無いか
    first = next((l.strip() for l in lines if l.strip() and not l.strip().startswith(("<!--", "## ", "!["))), "")
    first_talk = next((l.strip() for l in lines if SPEAKER.match(l.strip())), "")
    if style == "dialogue" and not first.startswith(f"**{Q}**: "):
        errors.append(f"E01: 記事が **{Q}**: で始まっていない → 先頭: {first[:40]}")
    elif style == "interview" and not first_talk.startswith(f"**{Q}**: "):
        errors.append(f"E01: リード文のあと、最初の発言は聞き手 **{Q}**: の質問にする → {first_talk[:40]}")
    elif not TALK and re.match(r"^(この記事では|本記事では|今回は)", first):
        errors.append(f"E01: 導入文（この記事では〜）で始めない。読者への問いか場面から入る → {first[:40]}")
    if any(l.startswith("# ") for l in lines):
        errors.append("E01: H1（# ）は入れない。タイトルは article_title に入れる")

    # E02: 話者の役割（話者ありのテイストだけ。解説役が質問ばかり・質問役が解説ばかりは逆転）
    if TALK:
        qa = {Q: [0, 0], A: [0, 0]}
        for line in lines:
            m = SPEAKER.match(line.strip())
            if m:
                is_q = any(k in line for k in ["？", "?", "ですか", "でしょうか", "ますか"])
                qa[m.group(1)][0 if is_q else 1] += 1
        if qa[A][0] > qa[Q][0] or qa[Q][1] > qa[A][1]:
            errors.append(f"E02: 話者逆転の疑い（{Q} 質問{qa[Q][0]}/解説{qa[Q][1]}, {A} 質問{qa[A][0]}/解説{qa[A][1]}）")

    # E03: 地の文の置き場所（対話＝置かない／インタビュー＝最初の ## より前のリード文だけ・3段落まで／地の文のテイスト＝見ない）
    # E04: 箱の外のリスト / E08: 1つの発言・段落の長さ
    in_box = in_comment = seen_h2 = False
    lead = 0
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if not s:
            continue
        if s.startswith("<!--"):
            in_comment = "-->" not in s
            continue
        if in_comment:
            in_comment = "-->" not in s
            continue
        if s.startswith(":::"):
            in_box = s != ":::"
            continue
        if in_box:
            continue
        if s.startswith("## "):
            seen_h2 = True
            continue
        if s.startswith("### ") or s.startswith("!["):
            continue
        sentences = len(re.findall(r"[。！？!?]", s))
        if SPEAKER.match(s):
            if TALK and sentences > 6:
                errors.append(f"E08: L{i} 1つの発言が{sentences}文（6文まで）")
            continue
        if re.match(r"^([-*] |\d+\. )", s):
            errors.append(f"E04: L{i} 箱の外ではリストを使わない（:::steps か :::point の中だけ）: {s[:40]}")
        elif style == "dialogue":
            errors.append(f"E03: L{i} 発言の外の文: {s[:50]}")
        elif style == "interview":
            lead += 1
            if seen_h2 or lead > 3:
                errors.append(f"E03: L{i} 地の文は最初の ## より前のリード文だけ（3段落まで）: {s[:50]}")
        elif sentences > 4:
            errors.append(f"E08: L{i} 1つの段落が{sentences}文（4文まで。スマホで読みやすい長さ）")

    # E05: note で表示できない書き方（表・水平線・mark）
    for i, line in enumerate(lines, 1):
        s = line.strip()
        if s.startswith("|"):
            errors.append(f"E05: L{i} 表は note で表示できない → :::point の中に「・」で並べる")
        if s == "---":
            errors.append(f"E05: L{i} 水平線は使わない")
        if "<mark>" in s:
            errors.append(f"E05: L{i} <mark> は note で表示できない → **太字** にする")

    # E06: 話者の書き方（全角コロン・話者以外の **名前**:。地の文のテイストでは使わない）
    for i, line in enumerate(lines, 1):
        for name in re.findall(r"\*\*([^*]+)\*\*[:：]", line):
            if not TALK:
                errors.append(f"E06: L{i} **{name}**: は話者の書き方。{STYLES[style]}では使わない（見出しなら ###）")
            elif name not in (Q, A):
                errors.append(f"E06: L{i} **{name}**: は話者専用の書き方。見出しなら ### を使う")
        if TALK and re.match(rf"^\*\*({Q}|{A})\*\*：", line.strip()):
            errors.append(f"E06: L{i} 話者のあとのコロンは半角 : にする")

    # E07: 箱（:::）の開きと閉じ / 箱の種類
    opens = [l.strip() for l in lines if l.strip().startswith(":::") and l.strip() != ":::"]
    closes = sum(1 for l in lines if l.strip() == ":::")
    if len(opens) != closes:
        errors.append(f"E07: ::: の開き{len(opens)}と閉じ{closes}が合わない")
    for o in opens:
        if not re.match(r'^:::(point|caution)\{title="[^"]+"\}$|^:::steps$', o):
            errors.append(f'E07: 使える箱は :::point{{title="..."}} / :::caution{{title="..."}} / :::steps だけ: {o}')
    if not any(o.startswith(":::point") for o in opens):
        errors.append("E07: :::point が1つも無い（1つ以上）")
    if style == "howto" and ":::steps" not in opens:
        errors.append("E07: ノウハウ・まとめでは :::steps（手順）が1つ以上要る")

    # E09: AI 臭い言い回し
    for p in AI_PHRASES:
        for i, line in enumerate(lines, 1):
            if p in line:
                errors.append(f"E09: L{i} AI 臭い言い回し「{p}」")

    # E10: 健康・効能・最上級（食品の広告で言えない・確かめられない）
    for p in RISKY:
        for i, line in enumerate(lines, 1):
            if p in line:
                errors.append(f"E10: L{i} 言えない表現の疑い「{p}」→ {CONFIG['forbidden']['reason']}")

    # E11: 相対の時制（半年後に読んでもおかしくないように）
    for p in RELATIVE_TIME:
        for i, line in enumerate(lines, 1):
            if p in re.sub(r"\([^)]*\)", "", line):
                errors.append(f"E11: L{i} 相対の時制「{p}」→ 2026年10月 のように絶対の日付にする")

    # E12: 長さと見出しの数（media.config.json の length / h2）
    n, lo, hi = body_chars(md), CONFIG["length"]["min"], CONFIG["length"]["max"]
    if not lo <= n <= hi:
        errors.append(f"E12: 本文 {n} 字（{lo:,}〜{hi:,}字）")
    h2, h2lo, h2hi = sum(1 for l in lines if l.startswith("## ")), CONFIG["h2"]["min"], CONFIG["h2"]["max"]
    if not h2lo <= h2 <= h2hi:
        errors.append(f"E12: ## 見出しが {h2} 個（{h2lo}〜{h2hi}個）")

    # E13: 画像（見出し画像1枚＋本文の図解1枚以上）
    eyecatch = re.findall(r"<!-- EYECATCH (images/\S+\.png) -->", md)
    figs = re.findall(r"!\[[^\]]+\]\((images/[^)]+\.png)\)", md)
    if len(eyecatch) != 1:
        errors.append("E13: 先頭に <!-- EYECATCH images/{id}-eyecatch.png --> が1つ要る（note の見出し画像）")
    if len(figs) < 1:
        errors.append("E13: 本文に図解が1枚も無い（## 見出しの直後に1枚以上）")
    for i, line in enumerate(lines, 1):
        if line.strip().startswith("!["):
            before = [l for l in lines[: i - 1] if l.strip()]
            if not before or not before[-1].startswith("## "):
                errors.append(f"E13: L{i} 図解は ## 見出しのすぐ次に置く")

    # E14: 画像のファイル（manual なら画像か指示文）が本当にあるか
    for rel in eyecatch + figs:
        png, prompt = ROOT / rel, (ROOT / rel).with_suffix(".prompt.txt")
        if not png.is_file() and not (IMAGE_MODE == "manual" and prompt.is_file()):
            errors.append(f"E14: 画像{'か指示文' if IMAGE_MODE == 'manual' else ''}のファイルが無い → {rel}")
    if re.search(r"!\[[^\]]*\]\(https?://", md):
        errors.append("E14: 画像は gen_image.py が出した images/... のパスだけ（ネットの画像は使わない）")

    # E15: 感嘆と笑い（！ の回数は media.config.json の exclamations。地の文のテイストは exclamations_prose。(笑 は 2 まで）
    ex = md.count("！") + md.count("!") - md.count("![")
    exr = CONFIG["exclamations"] if TALK else CONFIG.get("exclamations_prose", {"min": 0, "max": 5})
    exlo, exhi = exr["min"], exr["max"]
    if not exlo <= ex <= exhi:
        errors.append(f"E15: ！ が {ex} 回（{exlo}〜{exhi}回）")
    if md.count("(笑") + md.count("（笑") > 2:
        errors.append("E15: (笑 は 2回まで")

    # E16: 商品へのリンクは media.config.json の products の URL だけ
    shops = {re.sub(r"^https?://(www\.)?", "", u).split("/")[0] for u in PRODUCT_URLS}
    for url in re.findall(r"\]\((https?://[^)\s]+)\)", md):
        host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
        if host in shops and url not in PRODUCT_URLS:
            errors.append(f"E16: 登録していない商品ページ {url}")

    # E17: インタビュー・密着は本人の取材メモが要る（発言・場面を作らないため）
    if style in MEMO_STYLES:
        memo = ROOT / CONFIG.get("interview_file", "facts/取材メモ.md")
        text = memo.read_text(encoding="utf-8") if memo.is_file() else ""
        text = text[text.find("\n## "):] if "\n## " in text else ""  # 冒頭の説明は数えない
        body = re.sub(r"^#.*$|（[^）]*）|\s", "", text, flags=re.M)  # 見出しと（例）を除いた、本人が書いた分
        if len(body) < 50:
            errors.append(f"E17: {STYLES[style]}は本人の取材メモが要る → {memo.relative_to(ROOT)} に、実際に聞いた言葉・見た様子を書いてから書く")

    return errors


def main(argv):
    args = argv[1:]
    if not args:
        sys.exit(__doc__)
    style = args[args.index("--style") + 1] if "--style" in args else None
    if args[0] == "--id":
        from db import get_article
        row = get_article(int(args[1]))
        md, style = row["article_md"] or "", style or style_of(row)
    else:
        md = (ROOT / args[0]).read_text(encoding="utf-8")
        m = re.search(r"article_(\d+)\.md$", args[0])
        if not style and m:  # work/article_{id}.md なら、その記事のテイストを DB から読む
            from db import get_article
            style = style_of(get_article(int(m.group(1))))
    style = style or STYLE
    if style not in STYLES:
        sys.exit(f"[check] テイスト {style} は {' / '.join(STYLES)} のどれか")

    errors = check_article(md, style)
    print(json.dumps({"style": style, "chars": body_chars(md), "errors": errors}, ensure_ascii=False, indent=2) if errors
          else f"OK（{STYLES[style]}・本文 {body_chars(md)} 字）")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main(sys.argv)
