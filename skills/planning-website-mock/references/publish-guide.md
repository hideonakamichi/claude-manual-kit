# 公開の案内（Cloudflare Pages を初めて使う人へ）

⑤-5 で使う。公開は基本的に Claude がコマンドで自動で行うが、**実行する作業は1つずつ「何をするか・何が起きるか」を見せて、本人の OK をもらってから実行する**。人にしかできないのは最初の1回の3つだけ。

## 全体の流れ

```
【最初の1回だけ・人がやる】
 ① Cloudflare のアカウントを作る（無料）
 ② 届いたメールで本人確認をする
 ③ 「Authorize」を押す → このパソコンの wrangler に合鍵（トークン）ができる
        │
【Claude が自動でやる（各段で ▶ 確認）】
 ④ 公開先を作る
 ⑤ 外部サービスの設定を預ける（例: note のアカウント名）
 ⑥ 公開フォルダをアップロードして公開
 ⑦ 公開先で表示・連携・noindex を確かめる
```

- wrangler ＝ Cloudflare 公式の、ターミナルで使う道具。`npx` で一時的に取ってくるので、インストールは要らない（Node.js は要る）
- ①②③を Claude が代わりにやらない。本人のアカウントと本人の許可だから

## 人がやる3つ（Claude は1ステップずつ案内する）

| 段 | Claude がすること | 本人がすること |
|---|---|---|
| ③の前 | `npx wrangler login` を実行して、ブラウザで許可の画面を開く | ― |
| ①② | アカウントがなければ Sign up を案内。確認メールのリンクを押すよう伝える | 登録・メールの確認 |
| ③ | **押す前に、画面右上のアカウント（メールアドレス）が使いたいもので合っているか確かめてもらう** | 「Authorize」を押す |
| 確認 | `npx wrangler whoami` でログインできたか確かめ、アカウント名を伝える | ― |

つまずきやすいところ:
- 許可の画面は**数分で期限が切れる**。切れたら `wrangler login` を開き直す
- ブラウザがすでに Cloudflare にログインしていると、ログイン画面を飛ばして許可の画面が出る。どのアカウントか必ず確かめる
- メールの確認が済んでいないと、公開先の作成が `Your user email must been verified [code: 8000077]` で止まる。確認メール（なければダッシュボードの Resend）を案内する

## Claude が自動でやる部分（実行の前に必ず見せる）

見せる形の模範:

> **次に実行すること:** 公開先 `sample-site-test` を作る
> **コマンド:** `npx wrangler pages project create sample-site-test --production-branch main`
> **何が起きるか:** Cloudflare に公開先ができる。まだ中身はなく、URL も開けない
> 実行してよいですか？

| 段 | コマンド | 何が起きるか |
|---|---|---|
| ④ | `npx wrangler pages project create <名前> --production-branch main` | 公開先ができる。URL は `<名前>.pages.dev` |
| ⑤ | `npx wrangler pages secret put NOTE_USER --project-name <名前>` | 外部サービスの設定を Cloudflare に預ける |
| ⑥ | `npx wrangler pages deploy site --project-name <名前> --branch main` | 公開フォルダと `functions\` が公開される |
| ⑦ | 各ページ・画像・`/api/...` を開いて確かめる | 表示・連携・noindex の確認 |

- ⑥は**案件フォルダで実行する**（`functions\` を一緒に載せるため）
- ⑦では、公開フォルダの外（`design\`・差し替え表）が外から見えないことも確かめる。存在しない URL はトップページが返るので、中身で判断する
- `.html` 付きの URL は、末尾を外した URL へ自動で移る（308）。Cloudflare Pages の標準の動きで、問題ではない

## テスト公開のとき

- 検索エンジンに載らない設定（noindex）を入れる。各ページの `<meta name="robots" content="noindex, nofollow">` と、公開フォルダの `_headers`（`X-Robots-Tag: noindex, nofollow`）の両方。本番では両方を外す
- 非公開にするときは、公開先ごと削除する: `npx wrangler pages project delete <名前>`。**外に出す操作なので、本人が「消して」と言ったときだけ実行する**
- 合鍵を捨てるのは削除のあと: `npx wrangler logout`

## 外部サービスとの連携（note の例）

```
 本人：note に記事を書く
          │
 note.com（記事の一覧＝RSS）
          ▲ 1時間ごとに取りにいく
 Cloudflare 上の小さなプログラム（functions\api\note.js）
          │ 新しい3件を渡す
          ▼
 HP のトップに並ぶ
```

note に書くだけで、最大1時間で HP に出る。HP を公開し直す必要はない。

### note の記事も自動で作るなら（note 記事キット）

記事づくりは別のキット（note 記事キット・別配布）に任せる。このスキルからはつなぎ目だけ渡す。キットを持っていて本人が望んだら、HP の実装が終わったあとに使う。キットが無ければ、この節は飛ばす。

- 案件フォルダに `note-agent\` を並べて置く。HP 側（`site\` `functions\`）は書き換えない
- `design\要件.md` の目的・ターゲット → キットの `media.config.json`（reader / goal / tone）
- `design\素材\素材リスト.md` の ✅ だけ → キットの `facts\確かめた事実.md`（🟨 仮は写さない）
- 販売先 URL → products、`参考スタイル.md` の色 → image_style、`NOTE_USER` → note_user（同じ値）
- 記事の保存先（DB）は [tool-selection.md](tool-selection.md) の「Supabase か Cloudflare か」で決める
- 詳しい表はキットの README「HP キットとのつなぎ方」

## 公開したあとの更新

| 変えたいもの | やること |
|---|---|
| note の記事 | note に書くだけ（自動） |
| 写真 | 同じ名前で上書き → Claude に「公開して」（⑥を見せて OK をもらってから実行） |
| 文章・ページ | Claude に直してもらう → 「公開して」 |

写真を上書きしただけで自動公開したいときは、GitHub と Cloudflare をつなぐ方法がある。アカウントと設定が増えるので、本人が望んだときだけ提案する。

公開の記録（URL・アカウント・設定・コマンド）は `design\要件.md` に残す。
