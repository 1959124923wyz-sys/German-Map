# 德国地图维护5｜铁路热点区段相机契约（2026-10-12）

## 根因与修复范围
- topics/railway/overview.js 的 updateHotspots() 原 .hot-row.onclick 把阅读区段和 map.fitBounds() 强制定位绑在一起。点击列表就移动地图，违背维护4在所有专题建立的普通选择不改变地图相机原则。
- 现在点击十条高关注区段列表行仅选择真实铁路走廊、更新详情；新增每行单独「定位」按钮，才调用 fitBounds()，并同步选择对应资料。
- 不改 DB InfraGO 官方轨道、2026年9月 DB Timetables 观测、阈值、橙/红关注段或16州基础设施档案。未测量绿线仍须保留缺失口径说明。
- 对 topics/railway/tests/smoke_overview.py 在既有桌面和390px Chromium新增相机中心与zoom断言：点热点行不动，点定位按钮才移动。

## 质量验证及发布
- .github/workflows/railway-map-smoke.yml 在PR和合并后运行真Chromium，原轨道数据及几何回归须通过。
- 继续运行十专题外壳检查，Pages部署后另核对成功。
- 已关闭所有自动外部采集触发，手动更新规则持续生效。

## 下一批候选
- 毒品新闻列表 topics/drugs/news.js 的 openReport() 普通卡片点击仍触发 setView，既有卡片可能混用打开原文和地理定位；建议双控制并做桌面/移动端相机测试。
- 工业/基础设施/住房应使用真实 page.mouse.click 继续查上层Canvas/SVG拦截、跨州县选择及浮层关闭路径。
- 自动更新停用后逐专题核对数据年份、最后核验日期与静态快照元信息，防止误标实时。