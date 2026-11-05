"""E2E：用真的 Chrome 點完整份問卷，比對剪貼簿和 expected.txt。

跑法（需要本機有 Google Chrome）：
    uv run --with playwright python skills/decision-form/evals/e2e.py
"""

import functools
import http.server
import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
BUILD = SKILL / "scripts" / "build_form.py"


def build(data: dict, out: Path) -> subprocess.CompletedProcess:
    src = out.with_suffix(".json")
    src.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return subprocess.run([sys.executable, str(BUILD), str(src), str(out)], capture_output=True, text=True)


def check_rejects(tmp: Path) -> None:
    good = json.loads((HERE / "fixture.json").read_text(encoding="utf-8"))
    bad_cases = {
        "四個選項": lambda d: d["questions"][0]["options"].extend(
            [{"k": "C", "label": "c", "why": "c"}, {"k": "D", "label": "d", "why": "d"}]),
        "重複 id": lambda d: d["questions"][1].update(id="q1"),
        "缺 title": lambda d: d["questions"][2].pop("title"),
        "兩個推薦": lambda d: d["questions"][0]["options"][1].update(rec=True),
    }
    for name, mutate in bad_cases.items():
        data = json.loads(json.dumps(good))
        mutate(data)
        r = build(data, tmp / "bad.html")
        assert r.returncode != 0, f"{name} 應該被擋下，卻建成功了"
        print(f"✅ 擋下：{name}（{r.stderr.strip().splitlines()[-1]}）")


def main() -> None:
    expected = (HERE / "expected.txt").read_text(encoding="utf-8").rstrip("\n")
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        check_rejects(tmp)
        r = build(json.loads((HERE / "fixture.json").read_text(encoding="utf-8")), tmp / "form.html")
        assert r.returncode == 0, r.stderr

        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(tmp))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{server.server_port}/form.html"

        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            ctx = browser.new_context(viewport={"width": 390, "height": 844})
            ctx.grant_permissions(["clipboard-read", "clipboard-write"], origin=url.rsplit("/", 1)[0])
            page = ctx.new_page()
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.goto(url)

            page.click('.opt[data-k="A"]')
            page.fill("#note", "週五前做完")
            page.click("#next")

            h2 = page.locator("h2")
            assert "</script><b>放哪</b>" in h2.inner_text(), "標題的 HTML 應該原樣顯示成文字"
            assert h2.locator("b").count() == 0, "標題裡的 <b> 不能被當成 HTML"
            page.click("#next")

            page.click('.opt[data-k="talk"]')
            page.fill("#note", "第一行\n第二行")
            page.click("#next")

            page.uncheck('input[data-i="y"]')
            page.click("#next")

            page.fill("#note", "沒了")
            page.reload()
            assert page.locator("#note").input_value() == "沒了", "重新整理後答案應該還在"
            page.click("#next")

            page.click("#copy")
            page.wait_for_function("document.getElementById('ok').textContent.includes('複製好了')")
            got = page.evaluate("navigator.clipboard.readText()").rstrip("\n")
            browser.close()
        server.shutdown()

    assert not errors, f"頁面有 JS 錯誤：{errors}"
    if got != expected:
        print("❌ 剪貼簿和預期不同\n--- 預期\n" + expected + "\n--- 實際\n" + got)
        sys.exit(1)
    print("✅ 剪貼簿和 expected.txt 逐字相同")
    print(got)


if __name__ == "__main__":
    main()
