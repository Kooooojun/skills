#!/usr/bin/env python3
"""假 gh：讀 $SANDBOX/state.json，所有呼叫記到 $SANDBOX/gh_calls.log。"""
import json, os, sys
S = os.environ["SANDBOX"]; a = sys.argv[1:]
open(f"{S}/gh_calls.log", "a").write(" ".join(a) + "\n")
st = json.load(open(f"{S}/state.json"))
def pr(): 
    n = next((x for x in a[2:] if x.isdigit()), None)
    return next(p for p in st["prs"] if str(p["number"]) == n)
if a[:2] == ["search", "prs"]:
    print(json.dumps([{"repository": {"nameWithOwner": p["repo"]}, "number": p["number"], "title": p["title"], "url": p["url"]} for p in st["prs"]]))
elif a[:2] == ["pr", "view"]: print(json.dumps(pr()))
elif a[:2] == ["pr", "checks"]:
    for c in pr()["statusCheckRollup"]: print(f'{c["name"]}\t{c["conclusion"].lower()}\t{c.get("detailsUrl","")}')
elif a[:2] == ["run", "view"]: print(st["logs"].get(next(x for x in a if x.isdigit()), "no log"))
elif a[:2] == ["pr", "merge"]: print("merged (fake)")
else: print("{}")
