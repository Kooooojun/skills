# overnight 本機設定範本

複製到 `~/.config/overnight/local.md` 再改成你的情況。overnight 開工時會讀它，跟 SKILL.md 一起適用；
這個檔只在你電腦上，不會被分享。用不到的段落直接刪掉。

```bash
mkdir -p ~/.config/overnight && cp <本 skill 目錄>/local.example.md ~/.config/overnight/local.md
```

## 開工前檢查（追加）

- 記憶體：這台有 <N>GB，重工作（完整測試、build、回測）最多同時跑 <1 或 2> 份。
- 額度：<撞到用量上限時會不會自動換帳號？用什麼工具？沒有就寫「沒有，撞到就停」>
- <其他睡前要確認的環境，例如 VPN、外接硬碟、某個服務要先開著>

## 安全規則

- <你自己禁止的指令，例如 `git branch -D`、`rm -rf`；刪檔改用什麼（`trash`？）>

## 有配額或要付費的東西

- <例如某個資料 API 每日有配額：一晚只跑一份、用光就停並記成 blocked、幾點重置>

## 早上收尾（追加）

- <例如要更新某個狀態檔、清 worktree 的方式>

## 工具偏好

- <例如：中間交給 pstack:poteto-mode；reviewer 用哪種 agent；早上網頁用哪個 skill>
