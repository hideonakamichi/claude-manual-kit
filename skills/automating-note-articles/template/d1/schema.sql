-- note エージェント用 Cloudflare D1 スキーマ（D1 の中身は SQLite）
-- 流し方: python scripts/db.py init（DB が無ければ作ってから、この表を作る）
--
-- 記事1本 = articles の1行。status で今どこにいるかを表す。
--   idea     … 編集長が出したネタの候補（人が選ぶ前）
--   queued   … 人が採用したネタ。編集長が古い順に書かせる
--   approved … レビュアーが合格を出した。note に貼る下書きができている
--   skipped  … 3回差し戻しても合格しなかった
--   posted   … 人が note に公開した（note_url が入る）
--   dropped  … 人が不採用にしたネタ
-- 日時は UTC（日本時間の9時間前）。
-- products / research_notes / review_log は JSON を文字で入れる（db.py が出し入れのときに変換する）

CREATE TABLE IF NOT EXISTS articles (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  topic           TEXT NOT NULL,
  angle           TEXT,
  products        TEXT DEFAULT '[]',
  style           TEXT,   -- 記事のテイスト（dialogue / essay など）。空なら media.config.json の article_style
  style_reason    TEXT,   -- 編集長がそのテイストをすすめた理由
  status          TEXT NOT NULL DEFAULT 'idea'
                  CHECK (status IN ('idea','queued','approved','skipped','posted','dropped')),
  article_title   TEXT,
  article_md      TEXT,
  research_notes  TEXT,
  review_log      TEXT DEFAULT '[]',
  retry_count     INTEGER DEFAULT 0,
  skip_reason     TEXT,
  export_dir      TEXT,
  note_url        TEXT,
  posted_at       TEXT,
  created_at      TEXT DEFAULT (datetime('now')),
  updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_articles_status ON articles(status);
