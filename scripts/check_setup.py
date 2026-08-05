#!/usr/bin/env python3
"""盲點檢查 —— 六項機器驗，回答「我到底做好了沒」。

用法：
    python3 scripts/check_setup.py            # 全部檢查
    python3 scripts/check_setup.py --local    # 只跑不需要 gh 的那幾項

設計原則（跟課堂教的同一條）：查不到就說查不到，不要假裝綠的。
每一項不是 PASS 就是 FAIL 或 UNKNOWN —— UNKNOWN 代表「這台機器上我驗不了」，
不是「應該沒問題」。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PASS, FAIL, UNKNOWN = "PASS", "FAIL", "UNKNOWN"
MARK = {PASS: "✅", FAIL: "❌", UNKNOWN: "❔"}

# config.yaml 出廠時追的三個來源。還是這三個 = 學員還沒把它變成自己的。
SHIPPED_FEEDS = {
    "https://github.blog/feed/",
    "https://huggingface.co/blog/feed.xml",
    "https://techcrunch.com/category/artificial-intelligence/feed/",
}


class Result:
    def __init__(self, name: str, status: str, detail: str, fix: str = ""):
        self.name, self.status, self.detail, self.fix = name, status, detail, fix


def sh(args: list[str], timeout: int = 25):
    """跑一個指令，回 (returncode, stdout)。抓不到指令回 (127, '')。"""
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip()
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, ""


def gh_json(path: str):
    """打 GitHub API。回 None 代表查不到（沒 gh／沒登入／沒權限），不是「沒有」。"""
    rc, out = sh(["gh", "api", path])
    if rc != 0 or not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def repo_slug() -> str | None:
    rc, out = sh(["gh", "repo", "view", "--json", "nameWithOwner", "-q",
                  ".nameWithOwner"])
    return out if rc == 0 and out else None


# --------------------------------------------------------------------------
# 不需要 gh 的檢查
# --------------------------------------------------------------------------

def check_config_changed() -> Result:
    cfg = ROOT / "config.yaml"
    if not cfg.exists():
        return Result("config.yaml 換成你自己的來源", FAIL, "找不到 config.yaml",
                      "這個檔應該在 repo 根目錄，可能被誤刪了")
    urls = set(re.findall(r"url:\s*(\S+)", cfg.read_text(encoding="utf-8")))
    if not urls:
        return Result("config.yaml 換成你自己的來源", FAIL,
                      "config.yaml 裡沒有任何 url",
                      "在 feeds: 底下至少留一個 - name: / url: 的來源")
    if urls <= SHIPPED_FEEDS:
        return Result("config.yaml 換成你自己的來源", FAIL,
                      "還是出廠的那三個來源",
                      "打開 config.yaml，把 feeds 換成你真的想追蹤的網站 —— "
                      "這一步沒做，這個 repo 就還是我的、不是你的")
    added = urls - SHIPPED_FEEDS
    return Result("config.yaml 換成你自己的來源", PASS,
                  f"有 {len(added)} 個你自己加的來源")


def check_workflow_permissions() -> Result:
    wf = ROOT / ".github/workflows/weekly-digest.yml"
    name = "workflow 有寫入權限（contents: write）"
    if not wf.exists():
        return Result(name, FAIL, "找不到 workflow 檔",
                      ".github/workflows/weekly-digest.yml 不見了，報告不會被 commit 回來")
    text = wf.read_text(encoding="utf-8")
    if re.search(r"permissions:\s*\n\s*contents:\s*write", text):
        return Result(name, PASS, "還在")
    return Result(name, FAIL, "workflow 裡沒有 contents: write",
                  "GitHub 預設只給唯讀。少了這兩行，程式照跑、Actions 照樣綠，"
                  "但報告不會出現，而且錯誤訊息看不懂")


def check_tests() -> Result:
    name = "測試是綠的"
    rc, _ = sh([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
               timeout=90)
    if rc == 0:
        return Result(name, PASS, "全過")
    if rc == 127:
        return Result(name, UNKNOWN, "跑不起來（找不到 python）", "")
    return Result(name, FAIL, "有測試沒過",
                  "跑 python3 -m unittest discover -s tests -v 看是哪一條，"
                  "把錯誤整段貼給 AI：「請找出原因並修好，只修這個問題」")


def check_report_exists() -> Result:
    name = "真的產出報告了"
    out = ROOT / "reports" / "weekly"
    files = sorted(out.glob("*.md")) if out.exists() else []
    if not files:
        return Result(name, FAIL, "reports/weekly/ 底下沒有任何 .md",
                      "先在 Actions 分頁手動按一次 Run workflow，等 15-30 秒")
    latest = files[-1]
    body = latest.read_text(encoding="utf-8")
    if "沒有 GROQ_API_KEY" in body:
        return Result(name, FAIL, f"{latest.name} 產出來了，但裡面是「沒有金鑰」的降級訊息",
                      "報告有生成，但 AI 摘要那段是空的 —— 去把 GROQ_API_KEY 這個 "
                      "secret 設好，再跑一次")
    return Result(name, PASS, f"最新一份：{latest.relative_to(ROOT)}")


# --------------------------------------------------------------------------
# 需要 gh 的檢查（查不到就老實說查不到）
# --------------------------------------------------------------------------

NO_GH = ("裝了 gh 並登入才驗得到：brew install gh && gh auth login。"
         "不想裝也可以自己去 GitHub 頁面上看")


def check_actions_enabled(slug: str | None) -> Result:
    name = "Actions 已啟用"
    if not slug:
        return Result(name, UNKNOWN, "查不到這個 repo 在 GitHub 上的位置", NO_GH)
    data = gh_json(f"repos/{slug}/actions/workflows")
    if data is None:
        return Result(name, UNKNOWN, "問不到 GitHub", NO_GH)
    wfs = data.get("workflows", [])
    if not wfs:
        return Result(name, FAIL, "GitHub 上看不到任何 workflow",
                      "確認 .github/workflows/ 底下的檔案有推上去")
    bad = [w for w in wfs if w.get("state") != "active"]
    if bad:
        states = "、".join(sorted({w.get("state", "?") for w in bad}))
        return Result(name, FAIL, f"workflow 狀態是 {states}",
                      "打開你 repo 的 Actions 分頁，按那顆啟用按鈕。"
                      "fork 來的 repo 預設不會跑，這步沒做後面全部不會動")
    return Result(name, PASS, f"{len(wfs)} 個 workflow 都是 active")


def check_secret_set(slug: str | None) -> Result:
    name = "GROQ_API_KEY 這個 secret 設好了"
    if not slug:
        return Result(name, UNKNOWN, "查不到這個 repo 在 GitHub 上的位置", NO_GH)
    data = gh_json(f"repos/{slug}/actions/secrets")
    if data is None:
        return Result(name, UNKNOWN, "問不到 GitHub（也可能是你沒有這個 repo 的管理權限）",
                      NO_GH)
    names = {s.get("name") for s in data.get("secrets", [])}
    if "GROQ_API_KEY" in names:
        return Result(name, PASS, "有設（這裡只看得到名字，看不到值，本來就該這樣）")
    return Result(name, FAIL, "這個 repo 沒有叫 GROQ_API_KEY 的 secret",
                  "Settings → Secrets and variables → Actions → New repository secret，"
                  "名字要一字不差是 GROQ_API_KEY")


def check_workflow_ran(slug: str | None) -> Result:
    name = "workflow 在 GitHub 上真的跑過"
    if not slug:
        return Result(name, UNKNOWN, "查不到這個 repo 在 GitHub 上的位置", NO_GH)
    data = gh_json(f"repos/{slug}/actions/runs?per_page=10")
    if data is None:
        return Result(name, UNKNOWN, "問不到 GitHub", NO_GH)
    runs = data.get("workflow_runs", [])
    if not runs:
        return Result(name, FAIL, "一次都沒跑過",
                      "Actions → Weekly Competitor Digest → Run workflow，"
                      "不要等到下週一才發現沒設好")
    ok = [r for r in runs if r.get("conclusion") == "success"]
    if not ok:
        last = runs[0]
        return Result(name, FAIL,
                      f"跑過 {len(runs)} 次，但沒有一次成功（最近一次：{last.get('conclusion')}）",
                      f"打開 {last.get('html_url')} 看紅色那步的訊息，整段貼給 AI")
    return Result(name, PASS, f"最近 {len(runs)} 次裡有 {len(ok)} 次成功")


# --------------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", action="store_true",
                    help="只跑不需要 gh 的檢查")
    args = ap.parse_args()

    results = [
        check_config_changed(),
        check_workflow_permissions(),
        check_tests(),
        check_report_exists(),
    ]
    if not args.local:
        slug = repo_slug()
        results += [
            check_actions_enabled(slug),
            check_secret_set(slug),
            check_workflow_ran(slug),
        ]

    print("\n盲點檢查\n" + "─" * 58)
    for r in results:
        print(f"{MARK[r.status]} {r.name}")
        print(f"   {r.detail}")
        if r.status != PASS and r.fix:
            print(f"   → {r.fix}")
    print("─" * 58)

    n_fail = sum(1 for r in results if r.status == FAIL)
    n_unknown = sum(1 for r in results if r.status == UNKNOWN)
    n_pass = sum(1 for r in results if r.status == PASS)

    print(f"{n_pass} 項過 · {n_fail} 項沒過 · {n_unknown} 項這裡驗不了")
    if n_unknown:
        print("「驗不了」不等於沒問題 —— 那幾項要你自己去 GitHub 頁面上確認")
    if n_fail == 0 and n_unknown == 0:
        print("\n全部通過。它會在每週一早上自己跑，你可以把這件事忘掉了")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
