---
name: automating-sns-posts
description: 自分の文章（note 記事など）の1節を根拠に、Instagram のカルーセル（画像）とキャプションを作り、品質チェックを通ったものを保存して止まる「カルーセル作成キット」を案件に入れて動かすスキル。投稿は人が行う。Windows でも Mac でも動く。ひな形のコピー → ネタ元と brand.yaml を埋める → 1本作る → 人が確かめて自分で投稿、の順に進める。同じ配布物の note 記事キット（automating-note-articles）の記事をネタ元にできる。「Instagram の投稿を作りたい」「カルーセルを作って」「SNS 投稿を半自動で」「insta-autopost-kit」「automating-sns-posts」と依頼されたときに使う。
---

# カルーセル作成キット（入れて、動かす）

キットの中身は `template\` が正本。案件にはコピーして使う。
**仕組み・費用・つまずきは `template\README.md` が正本**（ここに同じことを書かない）。

```
① 置き場所 → ② ひな形をコピー → ③ ネタ元（自分の文章）を置く → ④ brand.yaml を埋める
→ ⑤ 1本作る（保存して止まる）→ ⑥ 人が確かめて、自分で投稿する
```

各段の確認が済むまで次へ進まない。手順が3つ以上の作業は、流れを先に見せて「1つずつ一緒に確認していきますか？（YES/NO）」と聞く。

## 進める前に伝えること（初回）

- **このキットは Instagram へ投稿しない。** 作って、`output\` に保存して止まる。投稿は、利用者が画像とキャプションを確かめてから、自分の手で行う
- **中止になる回がある。中止でも Claude の利用枠は同じだけ減る。** 少ない本数で始める
- 必要なのは Claude Code と Python と、日本語のゴシック体フォント。アカウントのパスワードや API キーは要らない

## ① 置き場所

案件フォルダに `insta-autopost-kit\` として置く（HP の `site\`、note の `note-agent\` と並べる）。既にあれば上書きしない。

## ② ひな形をコピー

`template\` を `insta-autopost-kit\` に丸ごとコピーする。コピー後、このフォルダで次を実行する（実行前に何が起きるかを伝える）。

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install pillow pyyaml
```

Mac は `python3 -m venv .venv`、`source .venv/bin/activate`。`.venv` を作らず、`python -m pip install pillow pyyaml` だけでも動く。

## ③ ネタ元を置く

- 利用者の文章（note 記事など）を `content\sources\*.md` に置く。**`## 見出し` の単位**で1節が1投稿の根拠になる。1節200字未満は使われない
- 公開前の下書きでも、**利用者が出してよいと決めた文章**なら置いてよい。人が投稿の前に必ず見るため。ただし、自分が内容に責任を持てる文章だけにする
- 節は作る予定の本数の2倍以上あると、繰り返しを避けられる

## ④ brand.yaml を埋める

同じ配布物の `automating-note-articles`（note 記事キット）の `media.config.json` が同じ案件にあれば、そこから引き継いで下書きを作り、利用者に確認する。無くても動く（`brand-setup` スキルが1問ずつ聞く）。

| brand.yaml | 引き継ぎ元 |
|---|---|
| audience（誰に） | `reader` |
| account.purpose / offer | `goal` / `products` |
| tone.voice | `tone` |
| tone.ng_words ・ content_sources.cautions | `forbidden.words`（食品の効能など。**必ず入れる**） |
| design.palette | HP と note の配色 |

埋めたら `python .claude/skills/shared/scripts/check_brand.py` が通ること。Instagram のアカウントがまだ無い人は、`account.handle` に仮の `@my_account` 形式の名前を入れる。

## ⑤ 1本作る（保存して止まる）

`template\.claude\orchestrators\banner-manual-orchestrator.md` に従って進める。

> 「banner-manual-orchestrator.md に従って、カルーセルを1本作って。投稿はしないで、output に保存して止まって」

- 10〜20分かかる。待つあいだ、選んだ節と、評価役の不合格の理由を一緒に読む
- 中止になったら、理由を読んでから材料か設定を直す。直さずにもう一度頼まない（利用枠を使う）
- 2〜3回作って、見た目と中身に納得してから次へ

## ⑥ 人が確かめて、自分で投稿する

保存先（`output\<日付>_<テーマ>\`）をエクスプローラーで開き、次の4つを利用者に確かめてもらう。

| 確かめること | 見るところ |
|---|---|
| 事実 | 画像とキャプションに書かれたことが、材料の節にあるか |
| 言えないこと | 「効く」「日本一」など、言ってはいけない言い方がないか |
| 読みやすさ | 文字が小さすぎないか、1枚に詰め込みすぎていないか |
| 自分らしさ | 自分のアカウントとして出してよい口調か |

投稿は、パソコンのブラウザで Instagram を開き、画像を番号順に選び、`caption.txt` を貼って行う。
**「シェア」を押す前に、もう一度読み返す。** 1つでも迷うなら、出さない。Claude は投稿を代行しない。

## この後の世界（卒業後）

ここまでは「作るのは AI、出すのは人」の範囲。**自動で投稿し、定期的に動かす世界もある。**
読み物として `template\docs\この後の世界.md` を案内する。自分で試すかどうかは、利用者が決める。

## Windows で動かすときの注意

- スクリプトは `python`（Mac は `python3`）で、相対パスで呼ぶ（許可リストがこの形と一致して判定するため）
- フォントは BIZ UD ゴシック → 游ゴシック → メイリオ の順に探す（Mac はヒラギノ）。見つからないときは画面にそう出る
- 保存先のフォルダ名は `output\YYYY-MM-DD_<英数字のスラッグ>` にする（日本語の名前は避ける）
