# planning-website-mock（HP づくりのスキル）

Claude Code で HP・Webサイト・LP を作るためのスキルです。いきなりコードを書かず、次の5段で、1段ずつ確認しながら進めます。

```
① 参考サイトを選ぶ（refero）
② 22項目を確認する（目的・ターゲット・導線・公開先など）
③ モックを作る（Claude Design）
④ 情報を渡す（写真・文章をフォルダと Excel で受け取る）
⑤ 実装して公開する（Cloudflare Pages）
```

## 置き方

1. このフォルダ（`planning-website-mock`）を、次の場所に丸ごと置く
   - Windows: `C:\Users\<あなたのユーザー名>\.claude\skills\planning-website-mock\`
   - Mac: `~/.claude/skills/planning-website-mock/`
   - `skills` フォルダが無ければ作る。`.claude` は隠しフォルダなので、エクスプローラーの「表示 → 隠しファイル」をオンにすると見える
2. Claude Code を起動し直す

特定の案件だけで使いたいときは、案件フォルダの `.claude\skills\` に置いてもよいです。

## 使い方

Claude Code に「HP を作りたい」と話しかけるだけで起動します。起動すると、最初に「HP づくりの流れで進めます」と宣言するので、それが出れば正しく動いています。

明示的に呼ぶときは「planning-website-mock で進めて」と書きます。

## 必要なもの

| もの | 使う段 | 費用 |
|---|---|---|
| Claude Code | 全体 | ― |
| claude.ai のアカウント | ③ モック（Claude Design） | Claude のプランに含まれる |
| Node.js | ⑤ 公開（wrangler） | 無料 |
| Cloudflare のアカウント | ⑤ 公開 | 無料（作り方はスキルが案内する） |
| Excel など | ④ 文章の受け渡し | ― |

## フォルダの中身

```
planning-website-mock/
├── README.md                     … この説明（Claude は読まない）
├── SKILL.md                      … スキル本体（流れとルール）
└── references/
    ├── grill-items.md            … ② で確認する22項目
    ├── tool-selection.md         … 公開先・保存先の選び方（DB は Supabase か Cloudflare か も）
    ├── claude-design-guide.md    … Claude Design を初めて使う人への案内
    └── publish-guide.md          … Cloudflare Pages での公開の案内
```

## 大事な約束

- 最初に流れを見せて「1つずつ確認しますか？（YES/NO）」と聞きます。この進め方を自分の CLAUDE.md に入れるかも1度だけ聞きます（OK のときだけ書き足します）
- 各段の終わりで、あなたの OK がないと次へ進みません
- 公開・削除など外に出す操作は、実行する前に「何をするか・何が起きるか」を見せて確認します
- 写真は、使う権利を持っているものだけを渡してください
- モックには仮の写真（Openverse の CC0 素材）が入ります。仮の写真が残っているうちは公開しません（テスト公開も同じ）。公開の前に、あなたの写真に替えるか、その写真の枠を外すかを決めてもらいます
