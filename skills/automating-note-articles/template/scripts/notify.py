"""通知を送る（編集長の完了報告と、run-agent.ps1 の失敗の知らせ）。送るのは編集長と run-agent.ps1 だけ。

  python scripts/notify.py check                  # 設定があるか（送らない）。無ければ足りない項目名を出して終了コード 2
  python scripts/notify.py test                   # 試しの通知を1通（準備の最後に、本人が「届いた」と言うまで）
  python scripts/notify.py send "件名" @work/report.txt
  python scripts/notify.py send "件名" "本文"
  python scripts/notify.py resend                 # work/未送信/ に残った通知を送り直す（編集長が起動したら最初に）
  python scripts/notify.py failure timeout logs\\run_….log "90 min"   # run-agent.ps1 専用。止まった知らせを1通

通知先は .env.local の NOTIFY_CHANNEL（gmail / slack / discord / chatwork / line）。
send が失敗したら本文を work/未送信/ に残し、終了コード 1 で終わる（次の resend で送り直す）。
設定が無いときの send は送らずに本文を画面に出す（チャットで動かすときは人が見ているため）。
自動実行は run-agent.ps1 が最初に check して、設定が無ければ記事を書かずに止まる。
"""
import json
import smtplib
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from email.message import EmailMessage

from _env import CONFIG, ROOT, env

UNSENT = ROOT / "work" / "未送信"

# 通知先ごとの .env.local の項目（値は画面に出さない）
CHANNELS = {
    "gmail": ("MAIL_TO", "SMTP_USER", "SMTP_PASSWORD"),
    "slack": ("SLACK_WEBHOOK_URL",),
    "discord": ("DISCORD_WEBHOOK_URL",),
    "chatwork": ("CHATWORK_API_TOKEN", "CHATWORK_ROOM_ID"),
    "line": ("LINE_CHANNEL_ACCESS_TOKEN", "LINE_USER_ID"),
}
# run-agent.ps1 が渡す止まった理由（ps1 は英語だけで書くため、日本語はここで組み立てる）
FAILURES = {
    "timeout": "時間切れ",
    "start": "Claude Code を起動できなかった",
    "unfinished": "編集長が最後（振り返り）まで終わらなかった",
}
# 1回で送れる長さ（超えたら分けて送る）
LIMITS = {"discord": 1900, "line": 4900, "slack": 3500, "chatwork": 9000}


def channel() -> str:
    name = (env("NOTIFY_CHANNEL") or "").strip().lower()
    if not name and env("SMTP_PASSWORD"):  # 前のキットの .env.local（Gmail だけの頃）
        name = "gmail"
    return name


def missing(name: str) -> list[str]:
    if name not in CHANNELS:
        return [f"NOTIFY_CHANNEL（{' / '.join(CHANNELS)} のどれか）"]
    return [k for k in CHANNELS[name] if not env(k)]


def _post(url: str, payload: dict, headers: dict | None = None, form: bool = False) -> None:
    if form:
        data = urllib.parse.urlencode(payload).encode("utf-8")
        ctype = "application/x-www-form-urlencoded"
    else:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        ctype = "application/json"
    req = urllib.request.Request(url, data=data, method="POST", headers={"Content-Type": ctype, **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            res.read()
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from None


def _chunks(text: str, size: int) -> list[str]:
    parts, buf = [], ""
    for line in text.splitlines(keepends=True):
        if len(buf) + len(line) > size and buf:
            parts.append(buf)
            buf = ""
        while len(line) > size:
            parts.append(line[:size])
            line = line[size:]
        buf += line
    return parts + ([buf] if buf else [])


def deliver(name: str, subject: str, body: str) -> None:
    title = f"{CONFIG.get('mail_prefix', '[note]')} {subject}"
    if name == "gmail":
        msg = EmailMessage()
        msg["Subject"], msg["From"], msg["To"] = title, env("SMTP_USER"), env("MAIL_TO")
        msg.set_content(body)
        host, port = env("SMTP_HOST") or "smtp.gmail.com", int(env("SMTP_PORT") or "465")
        with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context(), timeout=30) as smtp:
            smtp.login(env("SMTP_USER"), env("SMTP_PASSWORD"))
            smtp.send_message(msg)
        return
    for i, part in enumerate(_chunks(f"{title}\n\n{body}", LIMITS[name])):
        if name == "slack":
            _post(env("SLACK_WEBHOOK_URL"), {"text": part})
        elif name == "discord":
            _post(env("DISCORD_WEBHOOK_URL"), {"content": part})
        elif name == "chatwork":
            _post(f"https://api.chatwork.com/v2/rooms/{env('CHATWORK_ROOM_ID')}/messages", {"body": part},
                  {"X-ChatWorkToken": env("CHATWORK_API_TOKEN")}, form=True)
        elif name == "line":
            _post("https://api.line.me/v2/bot/message/push",
                  {"to": env("LINE_USER_ID"), "messages": [{"type": "text", "text": part}]},
                  {"Authorization": f"Bearer {env('LINE_CHANNEL_ACCESS_TOKEN')}"})


def save_unsent(subject: str, body: str, error: str) -> str:
    UNSENT.mkdir(parents=True, exist_ok=True)
    path = UNSENT / f"{datetime.now():%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps({"subject": subject, "body": body, "error": error, "at": f"{datetime.now():%Y-%m-%d %H:%M}"},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path.relative_to(ROOT))


def send(name: str, lack: list[str], subject: str, body: str) -> None:
    if lack:
        print(f"[notify] 設定が無いので送りません（足りない: {', '.join(lack)}）。本文:\n{body}")
        return
    try:
        deliver(name, subject, body)
    except Exception as e:
        path = save_unsent(subject, body, str(e))
        print(f"[notify] 送れませんでした（{name}）: {e}\n  本文は {path} に残しました。次の起動で送り直します")
        sys.exit(1)
    print(f"[notify] 送りました（{name}）")


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd, args = argv[1], argv[2:]
    name = channel()
    lack = missing(name) if name else ["NOTIFY_CHANNEL"]

    if cmd == "check":
        if lack:
            print(f"[notify] 設定が足りません（.env.local）: {', '.join(lack)}")
            sys.exit(2)
        print(f"[notify] 設定あり（通知先: {name}）")

    elif cmd == "test":
        if lack:
            sys.exit(f"[notify] 設定が足りません（.env.local）: {', '.join(lack)}")
        try:
            deliver(name, "試しの通知", "この通知が届いていれば、通知の設定は完了です。\n記事キットの完了報告は、ここに届きます。")
        except Exception as e:
            sys.exit(f"[notify] 送れませんでした（{name}）: {e}")
        print(f"[notify] 試しの通知を送りました（{name}）。届いたか確かめてください")

    elif cmd == "send":
        if len(args) < 2:
            sys.exit(__doc__)
        subject, body = args[0], args[1]
        if body.startswith("@"):
            body = (ROOT / body[1:]).read_text(encoding="utf-8")
        send(name, lack, subject, body)

    elif cmd == "failure":
        if len(args) < 2:
            sys.exit(__doc__)
        reason = FAILURES.get(args[0], args[0])
        detail = f"（{args[2]}）" if len(args) > 2 and args[2] else ""
        body = (f"自動実行が途中で止まりました。\n理由: {reason}{detail}\nログ: {args[1]}\n\n"
                "記事は書き終わっていないかもしれません。Claude Code に「ログを見て」と頼むと、原因を調べられます。")
        send(name, lack, f"失敗: {reason}", body)

    elif cmd == "resend":
        files = sorted(UNSENT.glob("*.json")) if UNSENT.exists() else []
        if not files:
            print("[notify] 未送信なし")
            return
        if lack:
            print(f"[notify] 未送信が {len(files)} 件ありますが、設定が無いので送れません（足りない: {', '.join(lack)}）")
            return
        for f in files:
            data = json.loads(f.read_text(encoding="utf-8"))
            try:
                deliver(name, f"{data['subject']}（{data['at']} の送り直し）", data["body"])
            except Exception as e:
                print(f"[notify] まだ送れません: {f.name}（{e}）")
                sys.exit(1)
            f.unlink()
            print(f"[notify] 送り直しました: {f.name}")

    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
