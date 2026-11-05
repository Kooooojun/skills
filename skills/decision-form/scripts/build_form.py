#!/usr/bin/env python3
"""把題目 JSON 塞進 assets/form.html，產生一份單檔問卷。

用法：python3 build_form.py questions.json out.html
資料格式見 SKILL.md「題目資料」。格式不對就印出哪一題錯、以非 0 結束，不產生檔案。
"""

import hashlib
import html
import json
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "form.html"
MAX_OPTIONS = 3  # 另外會自動加「想討論」


def fail(msg: str) -> None:
    sys.exit(f"build_form: {msg}")


def need_str(obj: dict, key: str, where: str, one_line: bool = False) -> None:
    if not isinstance(obj, dict):
        fail(f"{where} 的選項或項目要是物件，現在是 {obj!r}")
    if not isinstance(obj.get(key), str) or not obj[key].strip():
        fail(f"{where} 缺少文字欄位 {key!r}")
    # 會出現在貼回答案裡的欄位不能換行，否則會憑空多出一行假答案。
    if one_line and "\n" in obj[key]:
        fail(f"{where} 的 {key!r} 不能換行")


def validate(data: dict) -> None:
    if not isinstance(data, dict):
        fail("最外層要是物件")
    need_str(data, "title", "最外層", one_line=True)
    need_str(data, "date", "最外層", one_line=True)
    qs = data.get("questions")
    if not isinstance(qs, list) or not qs:
        fail("questions 要是非空陣列")
    seen = set()
    for n, q in enumerate(qs, 1):
        where = f"第 {n} 題"
        if not isinstance(q, dict):
            fail(f"{where} 要是物件")
        need_str(q, "id", where, one_line=True)
        need_str(q, "title", where, one_line=True)
        if "ref" in q:
            need_str(q, "ref", where, one_line=True)
        if q["id"] in seen:
            fail(f"{where} 的 id {q['id']!r} 重複")
        seen.add(q["id"])
        ctx = q.get("ctx", [])
        if not isinstance(ctx, list) or not all(isinstance(c, str) for c in ctx):
            fail(f"{where} 的 ctx 要是文字陣列")
        kinds = [k for k in ("options", "multi", "free") if q.get(k)]
        if len(kinds) != 1:
            fail(f"{where} 要剛好是 options／multi／free 其中一種，現在是 {kinds or '都沒有'}")
        if q.get("options"):
            opts = q["options"]
            if not isinstance(opts, list) or not 2 <= len(opts) <= MAX_OPTIONS:
                fail(f"{where} 要有 2～{MAX_OPTIONS} 個選項（「想討論」會自動加）")
            for o in opts:
                need_str(o, "k", where, one_line=True)
                need_str(o, "label", where, one_line=True)
                need_str(o, "why", where)
            ks = [o["k"] for o in opts]
            if len(set(ks)) != len(ks) or "talk" in ks:
                fail(f"{where} 的選項代號重複或用了保留字 talk")
            if sum(bool(o.get("rec")) for o in opts) > 1:
                fail(f"{where} 最多一個推薦")
        if q.get("multi"):
            items = q.get("items")
            if not isinstance(items, list) or not items:
                fail(f"{where} 是複選題，要有 items")
            for it in items:
                need_str(it, "k", where, one_line=True)
                need_str(it, "label", where, one_line=True)
            ks = [it["k"] for it in items]
            if len(set(ks)) != len(ks):
                fail(f"{where} 的 items 代號重複")


def main() -> None:
    if len(sys.argv) != 3:
        fail("用法：build_form.py questions.json out.html")
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    try:
        data = json.loads(src.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        fail(f"{src} 不是合法 JSON：{e}")
    validate(data)
    # 存答案的 key 預設跟著題目內容走：同一份問卷重開可以續答，改版後自動從頭開始。
    if not data.get("key"):
        canon = json.dumps(data, ensure_ascii=False, sort_keys=True)
        data["key"] = hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]
    # 跳脫 < 和 &，題目文字裡的 </script> 才不會提早結束 script 區塊。
    blob = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026")
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("/*__DATA__*/null", blob, 1).replace("__TITLE__", html.escape(data["title"]), 1)
    out.write_text(page, encoding="utf-8")
    print(f"✅ {out}（{len(data['questions'])} 題）")


if __name__ == "__main__":
    main()
