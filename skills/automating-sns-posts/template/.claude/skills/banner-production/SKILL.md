---
name: banner-production
description: Instagramフィード投稿用の図解カルーセル（3〜6枚、4:5 1080x1350）を生成する手順。theme-pickerが選んだ記事の節を根拠にcarousel_spec.jsonを設計し、DESIGN.md準拠のMinimalデザインでスライドを描画する。カルーセル作成パイプラインで、theme-pickerがテーマを選んだ直後に使う。
---

# banner-production

利用者の文章の1節を紹介する、Instagramフィード用の**図解カルーセル**
（表紙→中身→まとめの3〜6枚。基本は5〜6枚）を生成する手順。
目的は `config/brand.yaml` の `account.purpose` の達成。**「保存される投稿」にすること**を
最優先する（保存率が伸びの鍵）。

## 前提

- 作業前に `config/brand.yaml` を読む（読者・トーン・オファー・パレットの参照元）
- **theme-picker が返した `source_path`（記事の節の根拠テキスト）を全文読む。**
  画面に書く事実はその本文にあるものだけ。読まずに設計すると一般論になり中身が薄くなる
  （`references/carousel-spec.md` 冒頭）
- カルーセル構成（`carousel_spec.json`）は**オーケストレーター自身が設計する**。
  スキーマ・文字量上限・role別指針は `references/carousel-spec.md` に従う（厳守）
- デザインは `docs/DESIGN.md` のMinimal方針が絶対（3色以内・全テキスト日本語・
  1枚=1メッセージ・数字は意味とセット）。`scripts/render_slides.py` のレイアウトに
  組み込み済み（フォントサイズ・座標・線幅はすべて数値で固定）
- **画像は Pillow で決定論的に描く。画像生成AIは使わない。**
  同じ spec なら毎回同じ絵になる。見た目を変えたいときはプロンプトではなく
  `render_slides.py` の数値を直す
- **承認済み逸脱**: 最終スライド（summary）に限り、控えめな誘導1行（`cta`）を入れてよい。
  文言は `brand.yaml` の `offer.cta_line` を使う。`offer.enabled` が false の場合は
  `cta` を入れない。ボタン風・URL表記・煽り文言は引き続き禁止
- パレット3色は spec で**具体的なhex値として固定**する（`brand.yaml` の `design.palette`）。
  これが全スライドのスタイル一貫性を担保する

## 手順

スクリプトは素の `python`（Mac は `python3`）・フォアグラウンド・**相対パス**で実行する。
`.venv` の中の Python を直接指定するのではなく、`.venv` を有効にした状態で呼ぶ。

1. **carousel_spec.json を設計する**
   - `references/carousel-spec.md` の「記事紹介として設計する」・スキーマ・テーマ軸別
     推奨構成に沿って、`source_path` の節から 5〜6枚（cover 1 + content 3〜4 + summary 1）の
     構成を設計する。節が短く3枚ぶんの固有情報が取れないときだけ content を減らす
   - 文字量上限（headline 13字・sub 20字・points 各15字×3・cta 18字）を厳守。
     超えると詰め込みになり余白が死ぬ。削れないなら content を1枚増やして分割する
   - headline に半角スペースを1つ入れると、そこで2行に割られる（例「机の上の物 3つに絞る」）。
     入れなければ1行に収まるまで縮小し、収まらないときだけ中央付近で自動改行する
   - 設計後、同ファイル末尾の「設計時のチェック」を自分で通す
   - `OUTPUT_DIR/carousel_spec.json`（`output/<YYYY-MM-DD>_<テーマスラッグ>/`）に保存する

2. **スライドを描画する（1コマンドで全枚）**

   ```bash
   python .claude/skills/banner-production/scripts/banner.py --spec output/<YYYY-MM-DD>_<テーマスラッグ>/carousel_spec.json --out-dir output/<YYYY-MM-DD>_<テーマスラッグ>/
   ```

   - 描画は Pillow が行い、全枚で1秒未満。APIもサインインも不要
   - 出力は `slide_<n>_<role>_<ts>.png`（4:5、1080x1350）と `.layout.json`（描画パラメータ）
   - スクリプトが spec の構造検証・文字量チェックを行う。警告が出たら spec を見直す
   - 特定スライドだけ描き直すときは `--only-slide <番号>`（spec を直したあとに使う）
   - 「描画用の日本語フォントが見つかりません」と出たら、画面のメッセージを利用者に伝える
     （Windows は BIZ UD ゴシック・游ゴシック・メイリオのどれかが要る）

3. **evaluatorに評価を依頼する**
   - 生成した**全スライドの `.png`** と `carousel_spec.json`、**`source_path`** を
     evaluator サブエージェントに渡し、スライド単位＋カルーセル全体＋記事との照合の合否を得る
   - **不合格の場合**: 描画は決定論的なので、**同じ spec を描き直しても結果は変わらない**。
     不合格理由は必ず spec（文言・構成・煽り・NGワード）か、レイアウトの数値のどちらかに
     ある。spec の問題なら spec を直して該当スライドを描き直す:

     ```bash
     python .claude/skills/banner-production/scripts/banner.py --spec ... --out-dir ... --only-slide <不合格スライド番号>
     ```

     レイアウトの問題（文字が大きすぎる・余白が足りない等）なら、`render_slides.py` の数値の問題
     なので、勝手に直さず、中止して利用者に報告する
   - 再描画後、そのスライドと前後のスライド（一貫性確認のため）を evaluator に再提出する
   - 上限は `config/loop-limits.yaml` の `carousel_slide_regeneration`（スライドごと最大2回）。
     2回で合格しない場合は中止し、`CLAUDE.md` の失敗時ルールに従う

4. **採用スライドを確定する**
   - 各スライド番号につき**最新の合格 `.png` 1枚**を採用する（同番号で複数世代ある場合は
     タイムスタンプ最新の合格版）
   - 不採用版・`.layout.json` は `output/` 配下にそのまま残す（デバッグ用）
   - 次工程には採用スライドのパスを**表示順に**渡す

## 出力

- `output/<YYYY-MM-DD>_<テーマスラッグ>/carousel_spec.json`（構成設計書）
- `output/<YYYY-MM-DD>_<テーマスラッグ>/slide_<n>_<role>_<ts>.png`（4:5、1080x1350）
- 同ディレクトリに `.layout.json`（描画パラメータ。投稿には使わない）

## 次のステップ

採用スライドのパス一覧（表示順）と spec、**`source_path`** を `caption-writer` サブエージェントに渡して
キャプションを生成し、`caption.txt` を `output/<YYYY-MM-DD>_<テーマスラッグ>/` に保存する。
**この後、Instagram への投稿は人が行う。** 司令塔は `.claude/orchestrators/banner-manual-orchestrator.md` の
手順で、保存と作成記録のあと止まる。

---

## フォールバック: 単発1枚バナー（通常は使わない）

カルーセルが不要な特殊ケース（告知1枚もの等）では、単発モードを使える:

```bash
python .claude/skills/banner-production/scripts/banner.py --headline "<見出し>" --sub "<サブテキスト>" --out-dir output/<YYYY-MM-DD>_<テーマスラッグ>/
```

表紙スライドと同じレイアウトで1枚描く（パレットは `brand.yaml` の `design.palette`）。
キャプションと同じく、evaluator の評価を通してから人に渡す。
