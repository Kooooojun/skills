---
name: overnight
description: 夜班模式。使用者去睡覺時，把長任務整晚跑完；如果沒指定任務，就顧好使用者所有的 open PR。流程分三段：睡前先用選擇題問使用者；半夜自己判斷、修 CI、解衝突（有 pstack 的 poteto-mode 就交給它），merge 與部署要先過獨立 agent review；早上做一頁本機網頁，再用選擇題問使用者。只把真正關鍵的決策留給使用者。觸發詞：overnight、夜班、我要睡了、明早再看、整晚跑。
compatibility: 需要 git、gh CLI；排隊用 flock（沒有就用 mkdir 當鎖）；能開 subagent 的宿主（Claude Code、Codex 等）才能過 merge／部署的 review 關卡。
disable-model-invocation: true
argument-hint: "[任務描述，或 repo／PR URL…] [--until HH:MM]（預設：我所有 open PR，跑到早上 08:00）"
---

# Overnight 夜班

overnight 只做頭尾：睡前問一次、早上問一次；中間有 `pstack:poteto-mode` 就交給它，沒有就自己做。
它的價值是**規則**（什麼留給使用者、什麼不准做、什麼要先 review）和**介面**（使用者只被打擾兩次）。

`~/.config/overnight/local.md` 存在就先讀，裡面是這台機器的追加檢查與規則，跟本檔一起適用（兩邊衝突時以 local.md 為準）。不存在時，在開工提醒裡附一句：「可照本 skill 目錄的 `local.example.md` 建一份本機設定」。

## 1. 開工（2 分鐘內）

- **任務**：參數給任務就照做；給 repo 或 PR 就顧那些 PR；沒給就顧 `gh search prs --author=@me --state=open` 的所有 PR。
- **截止**：照 `--until`，沒給就到下一個 08:00。
- **輸出資料夾**：`OUT=${OVERNIGHT_DIR:-~/.local/state/overnight/<YYYY-MM-DD>/<workspace>}`。`<workspace>` 取 `git rev-parse --show-toplevel`（不在 git 就用目前目錄），去掉 `$HOME/` 後把 `/` 換成 `-`。同一晚可能有好幾份夜班，每份只讀寫自己的 `$OUT`。裡面放 `handoff.json`（格式見最後）、`decisions.tsv`、`morning.html`。
- **開工前檢查**（只讀，一分鐘內；夜班最常斷在環境，不是程式）：
  - 重工作（完整測試、回測、build）一次只跑一份：用 `~/.local/state/overnight/locks/<資源>.lock` 搭 `flock` 排隊（沒有 flock 就用 `mkdir <鎖>.d` 當鎖，做完刪掉）。鎖跨 workspace 共用，不放 `$OUT`。
  - 產物、快取、續跑點放 `$OUT`，不放 `/tmp`（重開機會清空）。
- **提醒使用者**：電腦不能睡、session 不能關。一句話講完，連同檢查發現的問題，然後直接開工，不等回覆。

## 2. 睡前選擇題

只讀快速掃描（讀任務，或每個 PR 跑 `gh pr view --json ...`），不改程式。
用第 4 節找出**現在就看得出來**的關鍵決策，例如 review 裡的「要不要…」、牽涉別人的 branch、範圍或截止不清楚、多件任務沒說哪件最重要（問「今晚一定要達成的是哪一件？」）。

用宿主的選擇題工具問（Claude Code 是 `AskUserQuestion`；沒有就在對話裡列編號選項），格式（第 5 節同）：
- 只問真的符合第 4 節的題目，不湊數；沒有就不問。
- 一次最多 4 題，多的分批，重要的先問；相關的合併。
- 每題 2 個選項，推薦的放第一並標「（建議）」，description 寫一句影響。

答案寫進 `handoff.json` 的 `bedtime_answers`。**這是整晚唯一能問的時機**，交接後再問只會讓流程卡住。

## 3. 交接

填好下面交接單的 `<…>`。有 `pstack:poteto-mode` 就呼叫它，把交接單當參數；沒有就把交接單當成你自己今晚的工作規則，照著做。

```
任務：<任務，或「把以下 PR 顧到合併，必要時部署：…」>
截止：<HH:MM>。我要去睡了，繼續做，不要停（going to bed, keep going）。
睡前我已經決定：<bedtime_answers，沒有就寫「無」>

這幾條規則優先於 poteto-mode 和所有 playbook：
1. merge 和部署每次都要先過下面的 review 關卡。不准直接 push 到 base／main、不准 release、不准繞過 branch protection。
2. 不准 force-push（含 --force-with-lease）或 rebase。衝突用 `git merge origin/<base>` 解再正常 push；衝突不是停下的理由（覆寫 Babysit 第 5 步），只有碰到關鍵決策的 hunk 才照第 4 條。
3. 不准 --no-verify；不准為了變綠改測試期望值或停用 check。不用破壞性指令（git branch -D、reset --hard、clean -f、rm -rf）：清 branch 用 git branch -d，刪檔用可還原的方式。<local.md 有安全規則就貼在這裡> 指令被擋就換允許的做法，不要停下等人。
4. 不准用選擇題工具或任何方式停下來問人。碰到關鍵決策：兩個選項都準備好（branch、worktree 或 diff），都不 push；寫進 <OUT>/handoff.json 的 decisions，然後做別的。
5. 每個非顯而易見的決定寫一行到 <OUT>/decisions.tsv：時間、決定、理由、還原方式。
6. 每做完一個單位，更新 <OUT>/handoff.json 的 items 與狀態。
7. 每次醒來（含排程或 loop 的喚醒）先看時間。過了截止或提早做完：不開新工作，把手上那步做完或退回，回到 overnight 第 5 節收尾。

什麼算關鍵決策：<第 4 節 1–7 條和判準，一字不改>
merge／部署前的 review 關卡：<第 4.5 節，一字不改>
這份清單優先於任何「能還原就別問人」的原則（例如 pstack 的 never-block-on-the-human）：碰到任何一條，就算可以 revert，也要留給我。
```

有 poteto-mode 就照它自己的路由做事（Autonomous run、Babysit、fix-ci、fix-merge-conflicts），這裡不重寫；沒有就自己逐個 PR 修 CI、解衝突、處理 review，每做完一個就回頭看時間。

## 4. 什麼事要留給使用者

**留到早上**（符合任一條就留）：

1. 超出授權：直接 push 到 base、release、force-push、刪 branch、改 repo 設定或 required checks。merge 和部署已授權，但要先過第 4.5 節。
2. 兩邊都改了行為，而且測試、spec、PR 說明都判斷不了哪邊對。以下也算：
   - 疊起來變成兩邊原本都沒有的新行為，例如「捨去」加「最低 20 元」。
   - 牽涉錢、時間、權限、資料的計算規則，即使看起來能並存、能 revert。
3. 要改測試期望值才能過，但 PR 說明沒寫到這個行為改變。
4. migration、刪資料、schema、auth、secret。secret 外洩時不要印出來，只回報風險。
5. 「要不要…」的產品或架構方向問題。
6. 同一個問題 fix → push → recheck 3 輪還是紅，或要大範圍重構才修得好。
7. 會花錢、要動別人的 branch，或要在 PR／issue 以外通知別人（聊天室、email、別人的 repo）。在自己的 PR 上回覆 review 不算，照常做。

**自己決定**（記進 `decisions.tsv`，附理由和 `git revert <sha>`）：lint、format、type 錯誤或明顯 bug；flaky／infra 只重跑一次；機械性衝突（lockfile 用套件管理工具重新產生）；機械性 review nit（改名、guard、typo），做完在該 PR 上回覆 reviewer 說明改了什麼。

**不要 push 會變紅的東西**：修好的部分先 push；跟上 base 後才變紅、而且要碰到 1–7 條才修得好（例如要改測試期望值），就不要 push 那個 merge，把它留成準備好的選項。

**判準**：1–7 條優先。都沒碰到時，判斷錯了能在 feature branch 用一次 revert 還原、且期間沒人受害，就自己決定；不能就留給使用者。若有 pstack 的 never-block-on-the-human，它只適用於 1–7 條都沒碰到的事。

## 4.5 高風險動作的 review 關卡

merge PR、部署：每次都要過，沒有例外。

**前提**（任一條不符就不叫 reviewer，直接不做）：
- merge：已 `git merge origin/<base>` 跟上 base、CI 全綠；沒有人類 reviewer 的 CHANGES_REQUESTED 或未回答的問題；沒碰到第 4 節 2–5 條。
- 部署：只用該 repo AGENTS.md 寫的方式；要部署的 commit 在 main 上且 CI 全綠。

**叫 reviewer**：派不出 reviewer（宿主不能開 subagent）就不做，記成 items 的 `blocked` 並寫原因；這是環境問題，不是決策，不要變成問使用者的題目。派一個全新的 subagent（不帶你的 context），只讀不改，不給你的結論。給它動作、PR 連結或 diff、CI 結果、repo 的 AGENTS.md 路徑；部署再給上次部署到這次之間的 commit。請它檢查 bug、有沒有碰到第 4 節 1–7 條、部署會不會影響正在用的服務或資料，最後一行只回 `PASS` 或 `BLOCK：<原因>`。

**看結果**：
- `PASS`：照做，在 `decisions.tsv` 記一行 `review PASS <動作>`，附 reviewer 重點和還原方式（merge 寫 `git revert -m 1 <sha>`，部署寫該 repo 的回滾方式）。
- `BLOCK`：不做。在 `decisions.tsv` 記一行 `review BLOCK <原因>`。能自己修就修完再派新的 reviewer；同一件事 BLOCK 兩次就寫進 decisions 留到早上。
- 部署完照 repo 的方式驗收；失敗照文件回滾，文件沒寫就停下留到早上。

## 5. 早上收尾

工作做完、截止到了，或流程中斷時：

1. **核對 `handoff.json`**：每個 item 以實際查到的為準（`gh pr view`、本機測試）。worker 說做完不等於 CI 綠。
2. **做網頁**：呼叫 `eli5` skill（沒有就自己寫簡單 HTML），主題是 `handoff.json` 的白話摘要：幾件事要你決定（每件 2 選項、標推薦）、修好什麼、卡住什麼、`decisions.tsv` 連結。存成本機 `$OUT/morning.html`，不發布到線上。
3. **回覆使用者**：`morning.html` 絕對路徑，加一行數字：要你決定幾題、完成幾項、卡住幾項。
4. **問選擇題**：有決策就用選擇題問（工具與格式同第 2 節）。使用者選完，把準備好的那個選項做完並 push；之後 merge 或部署一樣先過第 4.5 節。
5. **清 worktree**：這一晚建的 worktree，`git status` 乾淨、HEAD 已在 `origin/main` 或 PR 已合併、沒有程式在跑，就收掉（移除 worktree、`git worktree prune`、`git branch -d`）；其他保留並寫進 items。
6. **收工**：選擇題處理完，`run.status` 改 `done`。之後的新工作另開 `$OUT-day`，不寫進這一晚的檔案，免得被看成夜班沒做完。

## handoff.json

```json
{
  "run": {"task": "", "started": "ISO", "deadline": "ISO", "status": "running|done|stopped"},
  "bedtime_answers": [{"question": "", "answer": ""}],
  "items": [{"name": "owner/repo#12 或子任務名", "url": "", "state": "merged|deployed|done|needs_you|blocked|in_progress|untouched", "summary": "一句話"}],
  "decisions": [{"id": "D1", "item": "", "question": "", "why": "對應第 4 節哪一條",
                 "options": [{"label": "", "impact": ""}, {"label": "", "impact": ""}],
                 "recommend": 0, "evidence": "檔案:行號", "prepared": "準備好的 branch 或路徑"}]
}
```
