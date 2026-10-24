# Kooooojun's skills

照 [Agent Skills](https://agentskills.io/specification) 格式寫的 skills（一個資料夾一個 `SKILL.md`），Claude Code、Codex、OpenCode、Gemini CLI／Antigravity 等支援 Agent Skills 的 agent 都能用。說明以繁體中文撰寫。

## 安裝

**任何 agent**（用 [skills](https://github.com/vercel-labs/skills) CLI，會問你要裝到哪個 agent）：

```
npx skills add Kooooojun/skills
```

**Claude Code plugin**：

```
/plugin marketplace add Kooooojun/skills
/plugin install kooooojun-skills@kooooojun
```

**手動**：把 `skills/<名字>/` 整個資料夾複製到你的 agent 讀 skills 的資料夾（Claude Code 是 `~/.claude/skills/`，其他 agent 看它的文件）。

### 不同 agent 的差異

- 會用到「選擇題」與「subagent」。宿主有就用；沒有選擇題工具就在對話裡列編號選項，不能開 subagent 時 hotspot-review 改成依序分析，overnight 的 merge／部署會停在「卡住」不執行（安全的那一邊）。
- `overnight` 的 frontmatter 有 Claude Code 專用欄位 `disable-model-invocation`（只能手動 `/overnight` 觸發），其他 agent 會忽略。

## Skills

### go-deeper：更深，不是更大

把一個任務或 prompt 改寫成更深的版本：頂尖專家會多做什麼、最原始的材料在哪、用什麼方法與工具、什麼外部證據能證明結果是對的。最後交回一份可直接貼給 agent 的 prompt，**先給你審，你同意才做**。

適合大任務、怕走錯方向、或要把 prompt 交給別的 agent 時。說「深入一點」「頂尖專家會怎麼做」或 `/go-deeper` 就會用。

### overnight：夜班

去睡覺前打 `/overnight`，agent 整晚顧好你的 open PR（或你指定的長任務）：修 CI、解衝突、處理 review nit。

- 睡前用選擇題問你一次，早上做一頁本機網頁、再問一次。中間不打擾你。
- 錢、時間、權限、資料的計算規則、migration、方向性問題一律留到早上，兩個選項都先準備好。
- merge 與部署每次都要先過一個獨立 agent 的 review。不 force-push、不 rebase、不改測試期望值。

**選用**：裝了 poteto 的 pstack（[Claude Code 版](https://github.com/michael-denyer/pstack-claude)）會把中間的工作交給它的 `poteto-mode`；沒裝就由 agent 自己照交接單做。早上的網頁會用 `eli5` skill，沒有就自己寫簡單 HTML。

**本機設定（選用）**：`~/.config/overnight/local.md` 存在就會一起讀，放只屬於你這台機器的檢查與規則（記憶體、帳號切換、配額、工具偏好），衝突時以它為準。從範本開始：

```
mkdir -p ~/.config/overnight && cp skills/overnight/local.example.md ~/.config/overnight/local.md
```

用 plugin 或 npx 安裝的，範本在安裝後的 `overnight/` 資料夾裡。這個檔不在 skill 裡，不會被分享。

`evals/` 有一套假 GitHub 沙盒測試：`evals/harness/setup_sandbox.sh <dir> busy|quiet` 建沙盒，跑完用 `evals/harness/grade.py <run_dir> busy|quiet` 評分。

### hotspot-review：熱點架構審查

用 git 歷史找出最近（預設 30 天）最常被修的檔案組，每組派一位唯讀分析員逐筆讀 fix diff 找根因，判斷是不是同一個設計問題，寫出排序過的報告。你同意後，再做最多 3 個**純結構**重構 PR：先用特徵測試固定行為、寫新舊對照腳本、獨立 reviewer、squash 合併。

「不建議」是正常結果：被修很多次不代表結構有問題。

- 規則以 repo 的 `AGENTS.md`（或 `CLAUDE.md`）為準；repo 有 `.agents/hotspot-review.local.md` 會一起讀（刻意分離的路徑、要付費才能跑的指令等）。
- 雜訊檔案用環境變數 `HOTSPOT_NOISE` 追加排除。
- 一次完整分析約 5 位分析員 × 15 萬 token，開跑前心裡要有數。

## License

MIT
