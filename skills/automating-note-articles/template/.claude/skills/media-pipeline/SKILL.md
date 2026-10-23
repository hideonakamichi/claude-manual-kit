---
name: media-pipeline
description: オウンドメディア（note）記事パイプラインの編集長の手順。ネタ候補の提案、採用済みネタの選定、ライター（media-writer）→レビュアー（media-reviewer）の差し戻しループ（書くのは最大3回）、合格記事の note 用書き出し、完了通知1通までを定める。編集長（media-editor）専用。
user-invocable: false
---

# note 記事パイプライン（編集長の手順）

> **先に `media.config.json` を Read する。** この手順の `{質問役}` `{解説役}` `{会社}` `{読者}` などは、その値に置き換えて読む（対応は media-article-writer の冒頭と同じ）。

## 役割分担

| 担当 | 役目 | やらないこと |
|---|---|---|
| **編集長（media-editor）** | ネタ候補を出す・書く記事を選ぶ・ループを回す・書き出す・通知 | 記事を書く・審査する |
| **ライター（media-writer）** | 調べて書く・画像を作る・DB に入れる | 通知・状態（status）の変更 |
| **レビュアー（media-reviewer）** | 22項目で審査・小さな直し・合否 | 通知・状態の変更 |
| **人** | ネタを選ぶ・note に貼って公開する | ― |

## ワークフロー

```
1. 起動時チェック（毎回）
   python scripts/reflection.py recent media-editor --hours 24
   → 24時間以内に完了した実行があれば、人が「もう一度」と言っていない限り何もせず終える（重複防止）
   python scripts/notify.py resend
   → 前回送れなかった通知（work/未送信/）を送り直す。まだ送れなければ、今回の完了通知の「次にやること」に「通知の設定を確かめる（notify.py test）」と1行足す

2. 書く記事を選ぶ
   python scripts/db.py next {articles_per_run}
   → 件数は media.config.json の articles_per_run

3. queued が 0 件なら → ネタ候補を出して終える（下の「ネタ候補の出し方」）
   queued が 1 件以上でも、idea + queued が 3 件を切っていたら、記事のあとで候補を足す

3.5 記事を回す前に、調べものの準備を確かめる（queued が 1 件以上のとき）
   python scripts/web.py key
   → なしで、人がチャットで起動しているなら、ライターを呼ぶ前に「Jina のキーを入れますか」と聞く（下の「Jina のすすめ方」）
   → なしで、自動実行（run-agent.ps1）なら止めずに進め、完了通知の「次にやること」に「Jina のキーを入れると出典集めが安定します」と1行足す

4. 各記事で ライター → レビュアー のループ（書くのは最大3回＝直し2回）
   a. Agent(media-writer)   初回の執筆
   b. Agent(media-reviewer) 審査
   c. 合格 → status を approved にして書き出し（下）
      差し戻し → retry_count を +1。3回目の差し戻しなら skipped（理由つき）。それ未満なら Agent(media-writer) に修正依頼して b へ

5. 完了通知を1通だけ送る

6. Step Final（4層の振り返り）
```

## ネタ候補の出し方（編集長の仕事。記事は書かない）

読者は {読者}。狙いは {目的}。

- 1回に **ideas_per_batch 本**。`facts/確かめた事実.md` の「提案としてなら書けること」と、読者が知りたい一般的な話（出典が取れるもの）から作る
- すでにあるネタと重ならないこと（`python scripts/db.py topics` で確かめる）
- 会社の歴史・製法など、確かめた事実に無いことが中心になるネタは出さない
- 1本ずつ `topic`（読者の疑問の形。例: 〇〇はBにすると何が変わる？）・`angle`（読み終えて持ち帰ること・1文）・`products`（{商品} の key から0個以上）・**`style`（すすめるテイスト）と `style_reason`（理由・1文）** を決める

### テイストのすすめ方（1本ずつ・決めるのは本人）

`style` は `media.config.json` の `styles`（この案件で使ってよいもの）の中から選ぶ。形はライターの手順「テイストごとの形」の表。

| ネタの形 | すすめるテイスト |
|---|---|
| 「いつ・どれくらい・どうやる」に手順で答える | howto |
| 疑問から入って理由を知る | dialogue か essay |
| 使う場面を思い浮かべてほしい | story |
| 作り手・現場の話 | interview / documentary（取材メモがあるときだけ） |

- interview / documentary は、`interview_file`（取材メモ）にある人・場面から作るときだけすすめる。メモが無い・空なら、すすめずに完了通知へ「取材メモを書くと、作り手の話も書ける」と1行書く（発言・場面を作らないため）
- 同じテイストばかりにしない。10本なら2種類以上
- 理由は本人が判断できるように具体的に（例: 「振るタイミングと量を手順で答えるネタだから」）

`work/ideas.json` を Write ツールで作り、まとめて入れる（status は既定で idea）。形は `[{"topic": "...", "angle": "...", "products": ["sakura"], "style": "howto", "style_reason": "..."}, ...]`。

件数の確認は `python scripts/db.py sql "SELECT status, count(*) AS n FROM articles GROUP BY status"`。

```bash
python scripts/db.py add-ideas work/ideas.json
```

通知で候補を知らせる（件名「ネタ候補 {本数}本」）。本文には番号つきで topic・angle・**すすめるテイストと理由** を並べ（`python scripts/topics.py list` の形）、最後に選び方を書く:

```
採用するもの: python scripts/topics.py adopt 番号 番号 …（テイストはすすめたまま）
テイストを変える: python scripts/topics.py style 番号 テイスト（採用の前でもあとでも、書く前なら変えられる）
使わないもの: python scripts/topics.py drop 番号 …
（Claude Code に「12と15を採用、15は読み物で」と頼んでも同じ）
```

## Jina のすすめ方（キーが無いとき・推奨）

キーが無くてもページは読めるが、検索ができない。ライターは URL の見当をつけて読みにいくことになり、出典3件（信頼できる出典1件以上）が集まらずに差し戻されやすい。次の形で聞く:

- **推奨: 入れる。** 理由（出典集めが一番つまずきやすい所で、検索があると安定する）と、無料のキーで足りることを添える
- 入れるなら、手順（https://jina.ai でキーを作る → `.env.local` の `JINA_API_KEY=` に本人が貼る → `python scripts/web.py key` が「あり」）を流れで見せ、「1つずつ確認しますか？（YES/NO）」と聞く。キーの値はチャットで受け取らない
- 入れないなら、そのまま 4 へ進む（詰まったら差し戻しの理由に出る）

## Subagent の呼び方

**どの呼び出しも、プロンプトの1行目に `PARENT_RUN_ID={自分の AGENT_RUN_ID}` を書く。** 書かないと振り返りの親子がつながらない。

### ライター（初回）

```
Agent(subagent_type="media-writer", description="記事執筆", prompt="""
PARENT_RUN_ID={AGENT_RUN_ID}

記事ID: {id}
ネタ: {topic}
切り口: {angle}
触れる商品: {products}
テイスト: {style}（db.py next に出る。ライターの手順「テイストごとの形」に従う）

起動直後に Step 0 をしてから、この記事を書いて DB に入れ、報告フォーマットで返してください。
""")
```

### レビュアー

```
Agent(subagent_type="media-reviewer", description="記事審査", prompt="""
PARENT_RUN_ID={AGENT_RUN_ID}

記事ID: {id}
{2回目以降なら: これは {n} 回目の審査です。前回の差し戻し内容: {前回の NG 項目}}

起動直後に Step 0 をしてから、この記事を審査し、合格か差し戻しを返してください。
""")
```

### ライター（差し戻しの修正）

```
Agent(subagent_type="media-writer", description="記事修正", prompt="""
PARENT_RUN_ID={AGENT_RUN_ID}

記事ID: {id}
レビュアーから次の差し戻しを受けました。直して DB に入れ直し、報告フォーマットで返してください。

{レビュアーの返答そのまま}
""")
```

## 状態（status）を変えるのは編集長だけ

```bash
# 合格
python scripts/db.py set {id} status=approved
python scripts/export_note.py {id}        # note下書き/{id}/ ができる。下書きと画像の置き場所の file:/// リンクが出る
# 人がチャットで起動しているときは --open を付ける（下書き.html がブラウザで開き、画像が足りなければ置き場所のフォルダも開く）。
# 自動実行（run-agent.ps1）では付けない（誰もいない画面に窓が開くため）

# 差し戻しの回数
python scripts/db.py set {id} retry_count={n}

# 3回差し戻し → 見送り
python scripts/db.py set {id} status=skipped "skip_reason={理由}"
```

### 見送りのとき、再挑戦のすすめを考える（決めるのは人）

3回の差し戻し内容を読み、テイストを変えれば通りそうかを判断して、完了通知に書く。自分で requeue・style はしない。

- **テイストで直りそう**（形が合わない・話者や手順が不自然・長さが収まらない など）→ `styles` の中から別のテイストを1つすすめ、理由を1文
- **テイストでは直らない**（出典が集まらない・確かめた事実が足りない・ネタ自体が無理 など）→ すすめず、その理由と、人にできること（事実を足す・ネタを変える・drop）を1文

## 完了通知（1回だけ）

件名: `完了 {合格数}本 / 見送り {数}本`。本文の型:

```
■ 合格（note に貼れます）
・{id} {article_title}（{テイスト}・{字数}字・差し戻し{n}回）
  下書き: {export_dir}\下書き.html
  開く: {export_note.py が出した「下書き（ブラウザで開く）」の file:/// リンク}
  画像の置き場所: {export_dir}\images
  （通知でリンクが押せないときは、場所をエクスプローラーの上の欄に貼って Enter）
■ 見送り
・{id} {topic}（{テイスト}・3回差し戻し。理由: {理由}）
  再挑戦: {「{別のテイスト} なら通りそう（理由）」か「テイストでは直らない（理由）。{人にできること}」}
  戻すなら: python scripts/topics.py requeue {id} → python scripts/topics.py style {id} {テイスト}（style は書く待ちに戻してから）
■ 次にやること
・（image_mode が manual なら）下書き.html の「先に画像を作る」で画像を作り、決まった名前で images へ → 「{id} の下書きを作り直して」
・下書き.html をブラウザで開き（エクスプローラーでダブルクリック。VSCode で開くとコードが出るだけ）、ボタンを①から順に押して note で Ctrl+V（図解のあとは Enter を1回）→ 公開
・公開したら: python scripts/topics.py posted {id} 公開したURL
・残りの書く待ち: {queued の数}本 / 候補: {idea の数}本
```

```bash
python scripts/notify.py send "完了 1本 / 見送り 0本" @work/report.txt
```

- 人がチャットで起動しているときは、チャットの報告にも下書き.html と画像の置き場所の file:/// リンクを付ける（人がフォルダを探さないため）
- 通知先（Gmail・Slack など）は `.env.local` の `NOTIFY_CHANNEL` で決まる。編集長は送り先を気にしない
- 送れなかったとき（終了コード 1）: 本文は `work/未送信/` に残り、次の起動の resend で送り直される。止まらずに Step Final へ進み、振り返りの self_improvement に「通知を送れなかった（理由）」と書く
- 設定が無いとき: 本文が画面に出るだけ（チャットで動かしているときは人が見ている）。自動実行は run-agent.ps1 が先に止めるので、ここまで来ない
- 開始・途中・1本ごとの通知は送らない（自動実行が止まったときの知らせは run-agent.ps1 が送る）
- ライター・レビュアーは送らない

## 絶対ルール

- **記事を書かない・審査しない**（必ず Agent で呼ぶ）
- **差し戻しは3回まで**。それ以上は skipped にして次へ（人に聞かない）
- **差し戻しのまま approved にしない**
- **note には自分で投稿しない**（公開は人）
- 自分で動かすのは 1 → 6 まで。人の承認は要らない（ネタ選びと公開だけが人）

## 自己診断（quality_check に書く）

- ✅/❌ 24時間以内の重複実行を確かめた
- ✅/❌ 書く記事を status=queued から選んだ（idea を勝手に書いていない）
- ✅/❌ ライター・レビュアーを Agent で呼び、自分で書いていない
- ✅/❌ 全 Agent 呼び出しの1行目に PARENT_RUN_ID
- ✅/❌ 差し戻しは3回で打ち切った
- ✅/❌ 合格記事を export_note.py で書き出した
- ✅/❌ 起動時に未送信の通知を送り直した（resend）
- ✅/❌ 通知は最後の1通だけ
