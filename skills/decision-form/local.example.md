# decision-form 本機設定範例

複製到 `~/.config/decision-form/local.md` 後改成你自己的。這個檔不會被分享。
這裡寫的交付方式優先於 SKILL.md 的預設。

## 交付

- 在 Mac mini 上：把 `form.html` 改成看得懂的檔名，複製到 `~/remote-view/`，
  網址是 `https://<你的主機>.ts.net/view/<檔名>`（中文要 percent-encode）。
  給網址前先 `curl -s -o /dev/null -w "%{http_code}"` 確認回 200。
- 不在 Mac mini，或網址不通：才發 artifact。
- 不要在這台電腦開瀏覽器給我看，我通常不在電腦前。
