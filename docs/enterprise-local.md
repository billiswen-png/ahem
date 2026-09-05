# 第 2～5 層：本機企業工作台

本機 demo 最新收尾：[會議日期分析與備份保留管理](evidence/local-demo-final/README.md)。包含最新測試、運行截圖及「已實作但未啟用週期清理」等界線；歷史待辦請以此報告為準。

最新範圍已收斂為「不接外部服務，只完成本機 demo」。站內通知、自動事故與合成回報演練已加入，請見 [本機 demo 驗收與截圖](evidence/local-demo-alerts/README.md)。歷史章節的外部整合待辦不代表本次仍要求交付那些商用功能。

最新功能：已加入新增限時成員與憑證輪替 UI／持久化，請以 [本次憑證交付報告](evidence/enterprise-credentials/README.md) 的完成清單與限制為準。
這是人工交付的限時存取憑證，不是 Email 邀請或 SSO。歷史章節中「憑證輪替 UI 尚未實作」已被本輪取代。

最新上傳增量：已新增本機加密備份、驗證、新檔還原 CLI 與實機瀏覽器還原檢查。
最新完成／未完成矩陣、完整 log 與執行截圖請以 [本輪驗證報告](evidence/enterprise-recovery/README.md) 為準。
下方各次「未推送」為當時記錄，本輪經授權上傳獨立分支，仍不建立 PR／不合併 main。

## 最新增量：每日統計、成員停用與事故流程

本節取代下方旧版矩陣對「成員停用／事故處理」的未完成描述。只完成下列本機流程，並非所有商用能力完成。

- 第 2 層：每日匯入統計表，最近 30 天、UTC 日期、只計仍在保存期的資料。旧資料缺少時間則明確列為未納入；不是長期效率評分或真實會議日期趨勢。
- 第 3 層：管理員可停用／恢復其他同組織成員；停用會撤銷 session 並阻擋原憑證登入，狀態持久保存。禁止停用自己，普通管理員不能管理受限內容管理員。恢復使原憑證再度有效，不是憑證輪替。
- 第 5 層：管理員與客服可手動登錄固定服務代碼的事故，待確認 → 處理中 → 已結案；同服務不可重複開啟事故。事故按組織隔離、分頁，結案 90 天後清理。沒有自由輸入會議內容的欄位，結案不更改真實健康狀態。
- 新 API：`GET /api/trends`、`POST /api/members/status`、`GET/POST /api/incidents`、`POST /api/incidents/{id}`。所有寫入仍需 Origin、session、role、tenant 檢查。

資料庫採增量建表（disabled_members、meeting_imports、incidents），沒有改寫既有密文。
**停用成員後不要直接回復到舊版服務**：舊版不讀 disabled_members，會讓停用憑證重新有效；rollback 前須從私有身分配置移除被停用帳號，並重啟清除 session。

驗證：macOS／Python 3.13.5，完整套件 `662 passed, 21 skipped, 2 xfailed, 0 failed`，exit 0（28.01 秒）。
指令同下方完整套件命令；新增 `tests/test_enterprise_operations.py` 8 項測試，覆蓋角色／組織隔離、事故轉移、停用跨重啟持久性、統計日期缺失。
Playwright Chrome 六角色回歸通過；新增操作迴圈驗證每日統計、停用／恢復、事故建立／確認／結案，1440×1000 和 390×844 無橫向溢出／JS 錯誤。
本輪 log、截圖與臨時 UI 測試腳本保留 repo 外 `../outputs/enterprise-operations-20260905/`。Browser 技能未提供，使用既有 Playwright。

### 仍未完成（沒有假按鈕或完成宣稱）

| 項目 | 狀態／後續所需 |
|---|---|
| 真實會議日期長期趨勢、效率分析 | 需定義事件時間與指標，不能把匯入次數當效率 |
| 成員邀請、憑證輪替 UI | 尚未實作，需要安全交付及身分配置持久化流程 |
| SSO / MFA | 尚未實作／驗證，需要選擇 IdP、應用設定、回呼網址與測試帳號 |
| KMS 輪替、備份／還原、法規保留 | 本輪未實作；需獨立還原演練、金鑰生命週期與保存政策決策 |
| 真實監測、自動事故、通知投遞、值班整合 | 本輪僅手動事故流程；需服務訊號來源、接收對象與通知管道設定 |
| Raspberry Pi 實機、壓測、音訊低延遲 | 尚未驗證，功能測試不等於效能證據 |
| 商業合規認證 | 未完成；權限隔離不等於產業合規 |

本輪僅本機，未推送／未更新 PR。持久 demo 身分目錄位於 repo 外，勿上傳憑證。

## 2026-09-05 流程補齊

此版本是本機功能版，不是已通過金融、醫療或法律合規認證的產品。

| 層 | 本次可操作流程 | 尚未完成的正式產品能力 |
|---|---|---|
| 2 | 會議代碼／政策篩選、分頁、全篩選範圍統計、本頁 JSON 匯出 | 長期趨勢、統計匿名性評估與跨組織授權 |
| 3 | 成員登入數、終止工作階段、個人全部登出、分頁稽核與結果篩選 | 成員邀請／停用、SSO、MFA、憑證輪替 UI |
| 4 | 縮短保存期限、受限政策升級、禁止降級、內容讀取後定期重新檢查權限 | 法遵評估、legal hold、KMS 輪替、備份與災難復原演練 |
| 5 | 安全狀態歷程（最近 100 筆／30 天），現況過期顯示未知 | 真實監測 adapter、通知投遞、值班與事故處理整合 |

工作階段撤銷不等於停用憑證；有效憑證可以重新登入。成員配置仍由私有身分檔管理。
內容視窗每 15 秒檢查一次 access API，失去權限則清空；網路與背景分頁節流會影響偵測時間，
無法撤回已下載或截圖的內容。伺服器每次讀取內容仍即時檢查權限，不依賴輪詢。
接收 JSON body 後再次驗證 session，並在 body 收完後才讀取會議 grant／policy，避免等待期間的撤權失效。

新增 API：`GET /api/members`、`POST /api/members/revoke-sessions`、`POST /api/logout-all`、
`POST /api/meetings/{id}/policy`、`GET /api/meetings/{id}/access`、`GET /api/health/history`。
analytics 支援 limit（1–100）、offset、q（十六進位代碼前綴）、policy；audit 支援 limit、offset、outcome。
統計 total_count／total_minutes／total_interventions 針對全部篩選結果，meetings 僅為當頁。

效能範圍：列表有 SQL 分頁及索引、健康歷程上限；仍使用單程序同步 SQLite，
沒有宣稱已完成高併發優化、降低音訊延遲或 Raspberry Pi 實測。
資料庫啟動時新增索引與 health_history 表，不修改既有會議內容；部署前停止程序並備份 DB 與 KEK。
回復到前版本可讀取原有表；會遺失本次新 API／UI 能力，重啟後 session 均需重新登入。

### 本次驗證證據

macOS、Python 3.13.5、Playwright 使用本機 Google Chrome。

```bash
../ahem/.venv/bin/python -m pytest -q tests/test_enterprise.py tests/test_enterprise_workflows.py
# 44 passed, exit 0
PYTHONPATH=src:../outputs/enterprise-ui-20260905 ../ahem/.venv/bin/python -m pytest -p browser_channel -q -rs tests
# 654 passed, 21 skipped, 2 xfailed, 0 failed, exit 0 (28.16s)
../ahem/.venv/bin/python scripts/verify_enterprise_browser.py \
  --identities /tmp/ahem-complete-check-20260905/identities.json \
  --output ../outputs/enterprise-complete-20260905/screenshots \
  --url http://127.0.0.1:8892 --channel chrome
# 6 roles pass, zero page/console errors, exit 0
```

browser_channel 是 repo 外測試 adapter，只指定已安裝的 Chrome，未跳過安全檢查。
21 skips：17 私有 holdout 資料缺少、4 真實 Discord opt-in；2 xfail 為既有測試。
瀏覽器涵蓋登入／登出、匯入、授權／撤銷、內容、統計匯出、篩選、保存政策、
成員工作階段撤銷、稽核／健康／個人頁與 390px 手機無水平溢出。
第一輪腳本因未等待授權面板載入而逾時，補明確等待後完整重跑通過。
log 與真實執行截圖在 repo 外 `../outputs/enterprise-complete-20260905/`。
單元測試流程證據：`tests/test_enterprise_workflows.py`；瀏覽器操作證據：`scripts/verify_enterprise_browser.py`。
未驗證：正式憑證服務、Linux/aarch64 實機、高併發、災難復原、真實 Discord／語音 provider 端到端。
本次不推送、不更新 PR、不更改原始 demo。

## 後台 UI 整合

目前 UI 已更新為 v2：白底／冷灰側欄／靛紫操作、固定側邊導覽與手機頂部導覽。
新素材、原始提示詞和設計決策見 [enterprise-assets-v2](design/enterprise-assets-v2/README.md)。
實際新增 `theme-v2.css`，保留v1基礎控制樣式；下方v1素材紀錄為先前版本。
本次結果位於 repo 外 `../outputs/enterprise-ui-v2/README.md`。

登入頁已使用 `enterprise_ui/assets/login-background.png`；登入後按真實角色顯示
`roles-and-states.png` 的對應插畫。按鍵是 HTML/CSS，不使用生成圖片當可點擊熱區。
延續米白／深藍／霧金素材配色；未新增第三方登入或前端自行切換角色。

第 2 層是分析表格，第 3 層是匯入、授權／撤銷、內容用途與稽核頁，第 4 層依
regulated_content 許可開啟內容，第 5 層只讀固定健康狀態。實際 API 再次檢查所有權限，
前端省略無權限的操作只改善使用體驗，不替代伺服器授權。

UI 增加鍵盤焦點、可見欄位標籤、載入狀態、防止重複送出、JSONL 錯誤恢復、
關閉內容區、破壞性操作確認、成功／錯誤提示，以及過期回應不覆蓋新頁面的 revision 檢查。
伺服器回 401 後會清空已顯示內容；登入仍為本機存取憑證，不是 SSO 或帳密註冊系統。
使用 `textContent` 顯示會議資料；圖片不进入音訊／SSE 事件路徑。

瀏覽器測試可用 `--url http://127.0.0.1:8891 --channel chrome` 指定獨立本機實例及已安裝 Chrome。
這次操作截圖、額外互動測試與實際 log 留在 repo 外的
`../outputs/enterprise-ui-20260905/`；不要把其私有測試身分檔或金鑰加入 Git。
這是本機功能整合，不代表完成效能 roadmap、雲端監控 adapter、SSO 或商業合規部署。

此版本位於 `codex/enterprise-local`，基於安全分支 `8320bbe` 建立。
本次交付為可執行、可測試的本機功能版本；不推送、不更新 PR、不部署 demo 主機。

## 四層交付與驗收

| 層級 | 實作 | 使用角色 |
|---|---|---|
| 2 管理版 | 同組織跨會議數量、總時長、人數、發言段數、主席介入比較；不傳姓名、議題、逐字稿 | manager / observer |
| 3 企業版 | 匯入 JSONL、逐場 Viewer 授權／撤銷、內容檢視、刪除、稽核 | operator / viewer |
| 4 受限內容 | regulated 政策另要求身分設定中的 regulated_content=true；用途固定選項、加密保存、到期清除 | content-officer（具有內容許可的 operator） |
| 5 SaaS 後台 | 僅提供 allowlist 的元件代碼、狀態、回報時間；逾五分鐘變 unknown | support |

不同使用者由不同憑證登入；前端不能透過選單把自己升權。企業版 Operator 的一般內容權限
不代表可讀受限內容。觀察者沒有逐字稿 DOM，伺服器回應也沒有原始內容。
既有 spectator 與本工作台為獨立入口：本工作台不會改變既有 spectator 的授權設定。

## 架構

```text
Ahem event JSONL ── Operator 匯入 API ── 驗證／統計投影
                                      ├─ SQLite：白名單統計
                                      └─ EnvelopeStore：AES-256-GCM 事件密文

私有身分設定 ── 登入 ── 30 分鐘 HttpOnly / SameSite=Strict cookie
                         ├─ org-a Manager → org-a 統計
                         ├─ org-a Viewer → 授權會議 → 政策判斷 → 內容／用途稽核
                         ├─ org-a Operator → 匯入／授權／刪除／稽核
                         └─ org-a Support → org-a 健康狀態（無會議資訊）

60 秒清理工作 → 到期會議與授權刪除；稽核保留 90 天
```

SQLite 適用單機、單程序的本機版本。組織資料查詢、授權對象都由登入身分限制；
使用者不能在 API body 指定別的組織。登出／session 到期後 API 拒絕存取。
匯入事件上限 10,000 筆及 HTTP body 4 MiB；保存期限 1～30 天。

## 啟動合成資料版本

使用已安裝此 repo requirements 的 Python；從此 worktree 執行以下指令。
demo 產生器要求全新目錄，避免覆寫既有金鑰或資料。

```bash
PYTHONPATH=src python scripts/enterprise_local_demo.py --directory /tmp/ahem-enterprise-demo-new
PYTHONPATH=src AHEM_KEK_FILE=/tmp/ahem-enterprise-demo-new/kek \
  python -m meeting_host.enterprise \
  --identities /tmp/ahem-enterprise-demo-new/identities.json \
  --database /tmp/ahem-enterprise-demo-new/enterprise.db --port 8890
```

開啟 `http://127.0.0.1:8890/`，登入頁輸入相應本機身分憑證。
身分檔為 0600，存放於 repo 外。Token 不放 URL、不寫瀏覽器儲存空間、不回傳至 API，
後端以雜湊比對；登入後清空輸入欄。KEK 為另外的 0600 檔案。

預設六個示範身分：operator、viewer、manager、observer、support、content-officer。
示範只有公開合成資料。兩場會議為相同合成事件、不同政策，用來比較存取行為，
不能當作兩場真實會議的營運績效。

## 接入現有 Ahem 資料

Operator →「內容與授權」→ 選擇 `.events.jsonl` → 選擇團隊／受限內容及保存天數 → 匯入。
管理者重新整理即可看到投影後的統計。這是明確匯入流程，尚未掛接每場 live shutdown 自動同步。

API（除 login 之外都需 session；寫入需 Origin 與服務設定相符）：

| 路徑 | 方法 | 允許角色與用途 |
|---|---|---|
| /api/login、/api/logout | POST | 登入／撤銷目前 session |
| /api/me | GET | 登入身分與內容許可 |
| /api/analytics | GET | manager/observer/operator：同組織；viewer：僅授權會議 |
| /api/meetings | POST | operator 匯入 {events, policy, days} |
| /api/meetings/{id}/content | POST | viewer（需 grant）或 operator；regulated 另需許可；purpose=meeting_review 或 incident_review |
| /api/meetings/{id}/grants | GET/POST | operator 查看／修改同組織 Viewer grant；受限會議另需內容許可 |
| /api/meetings/{id} | DELETE | operator 刪除保存內容與 grant |
| /api/audit | GET | operator；不含會議原文、token、自由輸入用途 |
| /api/health | GET | support/operator；元件代碼、狀態、最後回報 |
| /api/health | POST | operator 回報 {component, state} |

健康代碼 component=discord/stt/tts/chair；state=ok/degraded/unavailable/unknown。
可由持有工作台 Operator 憑證的服務監測程序登入後回報。未回報與逾時一律顯示 unknown。
此版本沒有自動連線或探測付費雲端服務，也不會假裝即時健康資料已接上。

## 安全性與部署邊界

- CLI 僅綁定 127.0.0.1。需要遠端使用時，必須另外配置 HTTPS 與精確 Origin，
  不可直接把本機 HTTP 入口公開；create_app 的 HTTPS 設定會启用 Secure cookie。
- 身分清單是本機管理員配置。新增帳號、變更角色／內容許可、輪替 token 後重啟服務，
  所有 session 失效；此版本未接 SSO/MFA／企業人員目錄。
- 閱覽授權／撤銷存在資料庫並立即生效；拒絕、讀取用途、匯入及授權動作記入稽核。
- 稽核是可查詢的 SQLite 紀錄，非外部防竄改日誌。主機 root／持 KEK 者仍屬信任邊界。
- aggregate 為去識別統計，不是形式上的匿名性保證。小樣本組合仍可能被外部資訊推知身分。
- SQLite secure_delete 和到期清理適用活動資料庫；不代表清除備份、快照或 SSD 物理殘留。
- 原始 JSONL 來源不由此工作台刪除；如已有明文來源，需由資料擁有者另行管理保存期限。
- 此功能是受限會議的技術控制，不宣稱金融、醫療、法律合規認證。

## 驗證與回復

```bash
PYTHONPATH=src python -m pytest -q tests/test_enterprise.py
PYTHONPATH=src python -m pytest -q tests
python scripts/verify_enterprise_browser.py \
  --identities /tmp/ahem-enterprise-demo-new/identities.json --output /tmp/ahem-enterprise-evidence
```

瀏覽器腳本會真實匯入一場合成會議，請用獨立合成工作台執行。
驗證涵蓋組織隔離、內容政策、撤權、Origin、到期 session、加密重啟、清理、登入限速，
以及五種身分登入與頁面、匯入、授權撤銷／恢復、受限內容用途確認和手機尺寸。

回復：停止此獨立服務即可；原 demo worktree 與部署不受影響。保留私有 KEK 與資料庫，
以相同設定重新啟動可恢復資料。不得把私有身分檔或 KEK 納入 Git。
