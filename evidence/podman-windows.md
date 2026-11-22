# Windows / Podman 實跑摘要

來源：2026-11-22 使用者提供的 PowerShell 建置、測試與展示輸出。此檔為摘錄與摘要，非逐字日誌。

- Podman Client 5.8.10 (Windows amd64)；Server 5.8.10 (Linux amd64 Podman Machine，rootful)。
- 工具映像 role-agent-hw2:local：f584296764095ea902dd678758208822f69353d68a0ca7578497263f9ddb1e86。
- 容器 unittest：Ran 25 tests in 0.033s；OK。
- OpenClaw 映像 role-agent-openclaw:local：b3e667d8596009e61663f169aadf3837e01b46562db17102f60f11bd474e0a64。Node 22 被 OpenClaw 套件拒絕；改以 Node 24 後建置與 CLI 版本指令成功，輸出 OpenClaw 2026.9.6 (eb377ac)。
- 容器 demo：SCRIPTED_BACKEND_REAL_SQLITE；live_llm=false。2026-11-22 09:40（台北時間）。

| 案例 | 實際觀察 |
|---|---|
| write | memory_put 寫入 presentation，週五，版本 1 |
| recall | memory_get 查回週五展示及設備疑慮，版本 1 |
| correct | memory_correct 把日期更正為週六，版本 2 |
| unknown | 查詢未知餐廳回傳 found=false、record=null |
| invalid_json | 回傳 INVALID_MODEL_JSON，流程停止 |
| stale_update | 以版本 1 更新版本 2，工具拒絕並回傳 VERSION_CONFLICT |

Windows 主機透過 Linux VM 執行。這不代表已在兩個獨立平台重跑；尚未驗證 Gateway 推論、真實模型端到端流程、Telegram 或跨容器 volume 保存。workflow-trace.json 是先前本機執行的另一份同流程紀錄。
