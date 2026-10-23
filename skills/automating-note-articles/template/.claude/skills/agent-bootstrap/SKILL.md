---
name: agent-bootstrap
description: 編集長 / ライター / レビュアー 3 体の共通の起動と終了の手順。起動直後に振り返りの行を作り（Step 0）、終わる直前に4層の振り返りを書く（Step Final）。subagent で呼ばれても、run-agent.ps1 から起動されても同じ手順で動く。
user-invocable: false
---

# 共通の起動と終了（3体とも必ず守る）

## 用語

- **トップで起動**: `scripts/run-agent.ps1` から（または人がチャットで「編集長を起動」と言って）始まった場合。run-agent.ps1 からなら、プロンプトに `AGENT_RUN_ID` が書いてある
- **subagent で起動**: 編集長が Agent ツールで呼んだ場合。プロンプトの1行目に `PARENT_RUN_ID=N` がある

## Step 0 — 起動直後に必ず

1. プロンプトに `AGENT_RUN_ID=N` があれば、それが自分の番号。行は作らない
2. 無ければ行を作る（`{slug}` は自分の名前: media-editor / media-writer / media-reviewer）

```bash
python scripts/reflection.py start --slug {slug} --trigger subagent --parent {PARENT_RUN_ID があればその数字、無ければ 0}
```

出てきた数字が自分の `AGENT_RUN_ID`。以後の報告に必ず書く。

3. 前回の反省を読む（同じ失敗を繰り返さないため）

```bash
python scripts/reflection.py lessons {slug}
```

## Step Final — 終わる直前に必ず

`work/reflection_{AGENT_RUN_ID}.json` を Write ツールで作ってから記録する。

```json
{
  "what_done": "やったこと（箇条書き）",
  "quality_check": "自分の agent.md の自己診断項目を ✅/❌ で",
  "quality_score": 0,
  "self_improvement": "ルール・手順・スクリプトの直し候補",
  "content_improvement": "記事の中身・構成の進化案",
  "result_full": "編集長は通知本文そのもの。ライター・レビュアーは編集長への報告そのもの",
  "items_processed": 0, "items_succeeded": 0, "items_failed": 0
}
```

```bash
python scripts/reflection.py finish {AGENT_RUN_ID} @work/reflection_{AGENT_RUN_ID}.json
```

途中で止まるしかないとき（DB に繋がらない等）は `python scripts/reflection.py fail {AGENT_RUN_ID} "理由"` を書いてから終える。

## 4層の振り返りの役目

| 欄 | 中身 | 読む人 |
|---|---|---|
| `result_full` | 完了報告そのもの | 人 |
| `what_done` / `quality_check` | やったこと・ルールを守れたか | 人と次回の自分 |
| `self_improvement` | agent.md・スキル・スクリプトの直し候補 | 人（直すかは人が決める） |
| `content_improvement` | 記事の進化案 | 人 |

## 絶対ルール

- 振り返りを書かずに終えない（途中で止まったように見える）
- subagent は `PARENT_RUN_ID` を必ず `--parent` に渡す（親子のつながりが切れる）
- `.env.local` の中身（キー）を表示しない・ファイルに書き写さない
