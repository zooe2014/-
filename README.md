# 菜就多煉

## 線上預覽（Render）

本專案可透過 Render Blueprint 建立免費預覽服務。部署時會依 `database/schema.sql` 與 `database/seed.sql` 重建示範資料，不會使用或上傳本機的 `data/菜就多煉.sqlite3`。

1. 在 Render 連接此 GitHub 專案，使用 repository 內的 `render.yaml` 建立 Blueprint。
2. 確認服務方案為 Free 後建立服務；部署完成後，Render 會提供 `https://<服務名稱>.onrender.com` 網址，可分享給同伴預覽。

這是公開可連線的原型，沒有登入隔離；所有訪客會共用示範帳號的收藏與設定。Free 服務閒置後可能休眠，重啟或重新部署會重建示範資料，因此收藏與設定不保證保留。請勿在此版本放入個人資料或私密內容。

Render 官方說明：[Blueprint](https://render.com/docs/blueprint-spec)、[免費方案限制](https://render.com/docs/free)。
