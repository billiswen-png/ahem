# Ahem 工作型 UI v2

以清楚、熟悉的工作型產品為設計依據，不宣稱存在可驗證的「最受歡迎 UI」排名。
參考：[Linear](https://linear.app/features)、[Notion](https://www.notion.com/product)。
原創版面與素材，未複製商標。使用內建 image_gen，不使用外部付費 API／CLI。

## 設計規格

- 白色主區 #fff、冷灰側欄 #f7f8fa、字色 #20232b、靛紫 #6366cf、分隔線 #e6e8ed。
- 常駐側欄、頂端組織／角色及登出、內容區標題／刷新、開放式三項統計與表格。
- 14px 操作文字、31px 標題、7px圓角、有鍵盤焦點；手機改成頂部雙欄導覽。
- 權限決定導覽項目，manager只看分析、support只看健康；不能為模仿概念圖而顯示未授權操作。
- 所有互動與數字為原有真實 API。背景／角色用AI圖片，按鍵與細小圖示用HTML/CSS/SVG。
- 保留既有 Ahem 字標，概念圖額外畫出的三角商標不採用。

## 圖片

- [工作台概念](workbench-concept.png)：1536×1024，設計參考而非執行截圖。
- [元件集合](components.png)：設計參考，表單／按鍵以程式實現。
- 背景：`src/meeting_host/enterprise_ui/assets/login-background-v2.png`。
- 8款角色／空狀態素材：`src/meeting_host/enterprise_ui/assets/roles-and-states-v2.png`。
  4欄2列、RGBA；runtime按角色選用相應位置，未全部顯示在同一頁。
- 原 v1 素材保留，v2不覆寫原圖；未新增SSO或其他未實作按鍵。

完整提示詞：[PROMPTS.md](PROMPTS.md)。後端、主線 demo 與 PR 不因本次樣式更新而改動。
