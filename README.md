# 自動化工作流程設計 — 課後帶走包

這個 repo 裡有兩樣東西：

1. **課堂上做出來的那個東西** —— 每週一早上自動幫你整理一份中文摘要的競品監控器
2. **一位隨附的助教** —— 你 clone 回去打開 AI，它就知道怎麼帶你、怎麼檢查你

第 2 樣才是這包的重點。你不用記得課堂上講了什麼，讓它帶你走一遍就好。

---

## 三分鐘開始

```bash
git clone https://github.com/young-ai-courses/ai-workflow-workshop.git
cd ai-workflow-workshop
```

然後在這個資料夾裡打開 **Claude Code** 或 **Codex**，直接跟它講話就好。
這個資料夾裡住著一位助教，它知道那天課上講了什麼。

**三句話，看你現在需要哪一種：**

> 幫我複習

上課聽懂、回家忘光是正常的。它會把整條線重新串一遍，一次講一段，
你也可以只挑忘記的部分聽。

> 開始教我

它會問你一件你覺得浪費生命的重複工作，然後**一次一步**帶你把這個 repo
改造成解決那件事的自動化。不會一次丟一堆步驟給你。

> 檢查一下我做好了沒

它會跑一輪機器檢查，告訴你哪裡還沒好 —— 包括那些**畫面上看起來都對、
但實際上永遠不會跑**的地方。

（不知道要說哪一句，就打「助教」，它會問你。）

---

## 不想用 AI，自己來也可以

```bash
pip install -r requirements.txt
python3 -m unittest discover -s tests -v      # 先確認地基是好的
python3 scripts/check_setup.py                # 隨時問「我做好了沒」
```

`check_setup.py` 會查七件事，其中三件要裝 [gh](https://cli.github.com) 才驗得到。
**它查不到的會標 ❔，不會假裝是綠的。**

自己走的話順序是：

1. 改 `config.yaml` → 換成你要追蹤的來源
2. [console.groq.com](https://console.groq.com) 免費註冊拿一把 API key（不用信用卡）
3. 你的 repo → Settings → Secrets and variables → Actions → New repository secret，
   名字**一字不差**是 `GROQ_API_KEY`
4. **Actions 分頁 → 按啟用** ← 最多人漏掉這步，漏了就是設定全對但什麼都不會發生
5. Actions → Weekly Competitor Digest → Run workflow，等 15-30 秒
6. `python3 scripts/check_setup.py` 全綠才算完成

---

## 這裡面有什麼

```
├── CLAUDE.md / AGENTS.md              兩種 AI 的入口，內容一樣
├── .claude/agents/
│   └── teaching-assistant.md          助教本人（帶著整堂課的內容）
├── .claude/skills/
│   ├── workshop-guide/SKILL.md        手把手教學（一次一步）
│   └── blind-spot-check/SKILL.md      盲點檢查（要證據不要形容詞）
├── scripts/
│   ├── weekly_competitor_digest.py    課堂成果本體
│   └── check_setup.py                 七項機器驗
├── tests/test_weekly_digest.py        三條回測鎖
├── .github/workflows/weekly-digest.yml
└── config.yaml                        ← 你要改的就是這個
```

---

## 為什麼是「每週一早上自動收到摘要」

因為它同時符合三件事：有公開資料可以抓、有規律的觸發時機、輸出定義清楚。
你自己要自動化的東西只要也符合這三件，就能用同一套架構做出來 ——
換掉 `config.yaml` 是換來源，換掉 `scripts/` 那支程式是做完全不同的事，
**排程、執行、把結果存回來這三件一行都不用動**。

同樣架構可以拿去做：每日 standup（抓 git log）、客戶新聞追蹤（Google News RSS）、
論文追蹤（arXiv RSS）、SEO 排名監控、專案進度報告（GitHub Issues API）。

---

## 兩個會咬人的地方

**fork 或 clone 來的 repo，Actions 預設是停用的。** 這是最多人卡住的地方，
因為它不會報錯 —— 你設定全部做對，就是什麼都不會發生。

**`.github/workflows/weekly-digest.yml` 裡的 `permissions: contents: write` 不要刪。**
GitHub 預設的 workflow 權限是唯讀。刪掉之後程式照跑、Actions 照樣綠燈，
但報告不會出現，而且錯誤訊息很難懂。

這兩件 `check_setup.py` 都會幫你抓。

---

*2026-08-06 線上課「自動化工作流程設計」課後帶走包*
