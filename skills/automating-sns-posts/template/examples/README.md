# examples — 動作実証済みの実例

このフォルダは**実際に描画に成功した実例**のコピー。自分のアカウント用の生成物を
作るときの書き方の参考にする（テーマは実例のものなので、そのまま使わないこと）。

| フォルダ | 内容 |
|---|---|
| `carousel-4slides/` | カルーセル4枚構成の carousel_spec.json |

- これらの実例は、投稿を「ネタ元の1節の紹介」として作る方式にする前のもの。実際の生成物では、
  `carousel_spec.json` に `source_path`・`article_title` が入り、表紙とまとめにネタ元の短い名前が入る
  （書式は `.claude/skills/banner-production/references/carousel-spec.md`）。
  ここで見るべきは、構成の組み方・1枚あたりの文字数
- 描画して見た目を確かめるには:

  ```bash
  python .claude/skills/banner-production/scripts/banner.py --spec examples/carousel-4slides/carousel_spec.json --out-dir output/example/
  ```
