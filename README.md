# 基於樣本建模與分層記憶的個人化角色 Agent

指定作業二：可執行工具核心與 OpenClaw 接入候選版
徐少綸｜411278025｜人工智慧代理人原理及實務

## 目前可以驗證什麼

本包新增可獨立執行的樣本正規化、可審核角色設定發布、SQLite 細節記憶及受限工具循環。
25 項自動測試在交付環境通過；evidence/workflow-trace.json 使用**腳本化模型輸出＋真實資料庫**，不是實際 GPT 對話證據。
Windows 的 Podman 5.8.10 已建置兩個容器映像；工具容器 25 項測試通過，SQLite 展示流程已實跑。OpenClaw 容器通過 CLI 版本檢查，真實模型與第二平台尚未完成驗證。證據見 evidence/podman-windows.md。
未變更使用者原有模型、OAuth、Gateway、Telegram 或私人資料。

## 快速執行 已測試的工具核心

需求：Python 3.12；只有標準函式庫。以下從本目錄執行。

```sh
python -m unittest discover -s tests -v
python scripts/demo.py
python src/role_agent.py normalize data/samples.json --speaker Aria
python src/role_agent.py publish data/persona.json --approved
python src/role_agent.py tool memory_put '{"key":"presentation","value":"週五展示","source":"synthetic-msg-1"}'
python src/role_agent.py tool memory_get '{"key":"presentation"}'
```

預期：測試顯示 Ran 25 tests / OK；normalize 輸出 2 筆 Aria 文字；publish 輸出內容雜湊；get 返回 found=true、value=週五展示、version=1。
PowerShell 的原生程式 JSON 引號處理因版本而異；建議在 WSL 執行上述 JSON 範例。測試指令不含 JSON，在 PowerShell 可直接使用。

## 工具介面

所有工具透過 `python src/role_agent.py --data-dir runtime --user demo --role aria tool NAME JSON` 執行。
user/role 由信任的呼叫端指定，模型參數不允許覆寫；尚未接上 Telegram 使用者身分對應，不可直接公開多使用者服務。

| Tool | 必要參數 | 輸出／錯誤 |
|---|---|---|
| memory_put | key,value,source | 新記憶版本1；不同內容撞鍵時 KEY_EXISTS_USE_CORRECT |
| memory_get | key | found 與 record；查無時 false/null |
| memory_search | query | 最多10筆，字面子字串匹配，非向量語意搜尋 |
| memory_correct | key,value,source,expected_version | version+1；舊值留歷史；過期版本 VERSION_CONFLICT |
| memory_delete | key,confirmed=true | 刪除目前與歷史；未確認 CONFIRMATION_REQUIRED |

memory_delete 不在模型可選工具清單內，僅供經確認的管理操作。一般建立、查詢與更正會在 evidence trace 顯示參數、結果與錯誤。實際資料含隱私時不得公開原始 trace。
更正以資料庫 compare-and-swap 防止舊版本覆寫新資料。SQLite 檔案與索引不是加密儲存；需由主機限制檔案權限。

## 真實 OpenClaw 模型接入 尚待驗證

保留原有 OpenClaw 模型與 Codex OAuth，由本程式執行官方 `openclaw agent --agent ... --session-id ... --message ... --json`。
不使用 --deliver，因此測試不會主動傳 Telegram 訊息。

1. 先確認 OpenClaw Gateway 與目標 Agent 已能正常回覆；備份現有工作區，不要覆蓋日常角色。
2. 執行上面的 publish，再執行：

```sh
python src/role_agent.py chat '幫我記住週五要展示 我擔心設備出錯' --agent yunbot
python src/role_agent.py chat '我之前說展示是哪天 最擔心什麼' --agent yunbot
python src/role_agent.py chat '展示改週六了 請更正記憶' --agent yunbot
```

輸出含完整 JSON trace。確認新增、讀取、更正均有實際 tool_call / observation；未知事件不可編造。
若發生 BACKEND_RESPONSE_FORMAT，先以不含私人內容的簡短問題檢視目前版本 `openclaw agent ... --json` 結構；本接入器僅解析 result.payloads[].text 或 payloads[].text，不保證不同發行版本相同。
本程式每次模型呼叫使用新 session；跨輪記憶由 SQLite 提供，不依賴相同 session。角色草稿由已確認的 persona 傳入生成提示，並未自動改寫 OpenClaw SOUL.md。
本工具循環不是 OpenClaw 原生 function calling；它由模型輸出受限 JSON、Python 驗證並執行工具，再將 observation 交回模型。
**限制：對 OpenClaw 既有工具權限的限制不能只靠 prompt；live 前請使用已隔離、工具權限適當的課堂 Agent。**

openclaw/AGENTS.md 是直接從角色 Agent 操作記憶工具的另一種接入說明，並非已安裝的 Skill；切勿在 Agent 內遞迴呼叫 chat。

## Podman 工具核心 已在 Windows 實跑

```sh
podman build -f Containerfile -t role-agent-hw2:local .
podman run --rm role-agent-hw2:local
podman run --rm role-agent-hw2:local python scripts/demo.py
```

若使用 Linux/WSL，可用 `sh scripts/check_podman.sh` 保存版本、測試與 demo 紀錄。
容器內測試與 demo 使用臨時資料庫；要驗證持久化，使用獨立 named volume：

```sh
podman volume create role-hw2-data
podman run --rm -v role-hw2-data:/data:U role-agent-hw2:local python src/role_agent.py tool memory_put '{"key":"presentation","value":"週五展示","source":"synthetic-msg-1"}'
podman run --rm -v role-hw2-data:/data:U role-agent-hw2:local python src/role_agent.py tool memory_get '{"key":"presentation"}'
```

兩次是不同容器，第二次應仍返回週五展示。`:U` 僅用在這個獨立課堂 volume，不可對日常私人資料目錄隨意使用。
Python 工具容器不含 OpenClaw；只通過此測試**不等於完整 Agent 已容器化**。

## OpenClaw 容器 建置與 CLI 已驗證

`Containerfile.openclaw` 封裝 Node、OpenClaw、Python 及專案工具。依先前提供版本固定 OpenClaw 2026.9.6；Node 24 基底已成功建置，版本指令輸出 OpenClaw 2026.9.6；Gateway 與模型推論待驗證。底層映像僅固定標籤，正式重現時另記錄 image digest。

```sh
podman build -f Containerfile.openclaw -t role-agent-openclaw:local .
podman volume create role-hw2-openclaw
podman volume create role-hw2-project
podman run --rm -it -v role-hw2-openclaw:/home/node/.openclaw:U role-agent-openclaw:local onboard
```

onboard 由使用者在獨立課堂設定中完成既有類型的 Codex OAuth 認證與模型選擇；不得把 OAuth token 或 Bot token 寫進 repo/image。此步會建立新展示狀態，並不搬動或修改日常設定。
接著啟動容器；若 onboarding 未設 local gateway，先依該版本 CLI 指引完成本機 Gateway 設定。

```sh
podman run -d --name role-hw2-gateway -p 127.0.0.1:18799:18789 -v role-hw2-openclaw:/home/node/.openclaw:U -v role-hw2-project:/home/node/role-data:U role-agent-openclaw:local
podman logs role-hw2-gateway
podman exec role-hw2-gateway python3 src/role_agent.py publish data/persona.json --approved
podman exec role-hw2-gateway python3 src/role_agent.py chat '幫我記住週五要展示' --agent main
podman exec role-hw2-gateway python3 src/role_agent.py chat '展示是哪一天' --agent main
```

main 是獨立 onboarding 預設 Agent；若建立其他展示 Agent，請指定對應 ID。原有 yunbot 的資料不會自動出現在新 volume。
範本不預載 llama.cpp / EmbeddingGemma，因這次使用 SQLite 結構化細節記憶；原有向量索引屬互補的未整合層。若期末恢復本機嵌入服務，應另以容器封裝、提供模型取得方式與跨架構驗證。
Telegram 是外部服務，不需要把 Telegram 伺服器封裝；本專案對應的 Gateway/通道程式需要在容器內。這次未設定 Bot token，也未做 Telegram 收發實測。

## 後續驗證與繳交步驟

- 後續啟動已建置的完整 Gateway，保存輸出。
- 完成至少一個真實模型的完整工具循環、兩個失敗情境的證據。
- 以合成資料驗證不同 user/role 邊界、重啟後保存及設定版本載入。
- 至少再選一個作業系統實跑相同案例；Windows/macOS 先啟動 Podman machine。Apple Silicon 另確認 ARM64 套件相容性。
- 將程式與去識別證據上傳自己的 GitHub Repository，分享給老師／助教；在提交說明填入真實網址。
- 隨驗證結果更新 PDF；本版報告保留腳本展示與真實模型驗證的區別。

## 參考

教授《AI Agent 課程作業與評分規範（4次作業）》第5–7、10、14–15頁；數位學院作業二頁。
OpenClaw CLI：https://docs.openclaw.ai/cli/agent
OpenClaw Podman：https://docs.openclaw.ai/install/podman
Podman：https://podman.io/docs/installation

本包不包含私人聊天紀錄、不聲稱還原任何真人；角色樣本全為合成。沒有上傳 GitHub，因本環境未取得使用者 Repository。
