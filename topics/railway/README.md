# BahnMonitor · 德国铁路运行专题

德国地图平级铁路主题。数据：DB InfraGO 2026 官方铁路网络线形、德铁时刻表 API 2026-09 停靠观测（Deutsche Bahn Data, Piet Brömmel; CC BY 4.0: https://github.com/piebro/deutsche-bahn-data）。独立分析 RB、RE、ICE/IC 与 HLB、BRB、ERB、NWB、OE。未染色线路无足够匹配观测，不等于运行正常；区间到站准点率不是轨道致晚点率；停靠取消标记不是整趟取消或旅客途中抛置的确证。

发布资源使用单独 JS 数据分片，加载顺序由 index.html 定义；全部数据内置 GitHub Pages，无需请求第三方轨道瓦片。源 Parquet 和六份官方基础设施 CSV 不发布到网站，详见本地 v14 交接归档。
