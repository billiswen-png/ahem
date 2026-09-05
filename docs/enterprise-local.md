# 第 2～5 層：本機企業工作台

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
