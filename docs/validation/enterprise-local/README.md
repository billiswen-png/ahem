# 第 2–5 層本機驗證紀錄

日期：2026-09-05。環境：macOS Darwin arm64、Python 3.13.5、Chromium headless。
基底：8320bbe；獨立 worktree `ahem-enterprise`／`codex/enterprise-local`。
僅新增獨立服務、UI、測試、文件；沒有修改原 demo 執行路徑，沒有 push 或 PR 更新。

## 實際測試

```sh
set -o pipefail
PYTHONPATH=src ../ahem/.venv/bin/python -m pytest -q -rs tests | tee /tmp/ahem-enterprise-final-tests.txt
```

結果：**636 passed、21 skipped、2 xfailed、0 failed；exit 0；23.68 秒**。
完整輸出：[pytest.txt](pytest.txt)。新增 enterprise 測試為 26 個。
21 skips：17 個缺少不公開的 holdout 資料，4 個真實 Discord opt-in；詳見 log 檔案／行號。
既有 xfail 不等於真實服務驗證通過。

```sh
../ahem/.venv/bin/python scripts/verify_enterprise_browser.py \
  --identities /tmp/ahem-enterprise-final-20260905/identities.json \
  --output docs/validation/enterprise-local
../ahem/.venv/bin/python -m bandit -q -lll src/meeting_host/enterprise.py
../ahem/.venv/bin/python -m compileall -q src/meeting_host/enterprise.py scripts/enterprise_local_demo.py scripts/verify_enterprise_browser.py
```

三個指令均 exit 0。Bandit 僅檢查 high severity，不代表無任何安全風險。
瀏覽器結果：[browser-results.json](browser-results.json)，五個角色均無 page error。
實際操作含匯入 JSONL、撤銷／恢復閱覽授權、受限內容用途確認、登出、390px 手機無頁面溢出。

## 可核驗邏輯與畫面

| 層級 | 證據 |
|---|---|
| 2 管理分析 | [manager.png](manager.png)、[manager-mobile.png](manager-mobile.png)；API 只投影數字，沒有姓名、逐字稿、主題 |
| 3 權限分離 | [operator.png](operator.png)；test_role_content_and_tenant_matrix 與授權／撤銷、跨 tenant 測試 |
| 4 受限內容 | [content-officer.png](content-officer.png)、[observer.png](observer.png)；內容許可與目的檢查在解密之前，加密重啟、到期刪除測試 |
| 5 客服狀態 | [support.png](support.png)；只回 allowlist 狀態，不回原始錯誤訊息；過期狀態顯示 unknown |

畫面採用 repo 公開的 `examples/synthetic-meeting.events.jsonl` 合成資料，不是真實客戶會議。
管理版截圖是匯入前兩場；Operator 操作新增一場後，其餘內容頁為三場，差異為測試流程造成。
實際 Ahem 主席發言事件為 `spoken`；test_actual_ahem_event_contract 驗證原始 JSONL
有 15 段與會者發言、3 位參與者、1 次主席介入，UI 也斷言主席原文出現。

## 未驗證與產品邊界

這是第 2–5 層的本機可操作 MVP，不是完成商業上線／產業認證。
未驗證 Raspberry Pi 5/Linux 實機、真實 Discord／雲端語音、SSO、正式 HTTPS 反向代理、
多程序負載、外部不可竄改稽核與備份銷毀。狀態只接收 allowlist 回報，不自動探測真實供應商。
組織分析目前為同 tenant 多場會議數字彙整，尚無完整部門目錄或長期趨勢評分。
root 或持 KEK 者仍可取得內容；不是對主機管理員的端對端保密方案。
詳細架構、啟動、回復及限制見 [enterprise-local.md](../../enterprise-local.md)。
