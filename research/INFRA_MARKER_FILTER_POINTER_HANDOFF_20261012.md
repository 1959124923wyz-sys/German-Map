# 维护5｜基础设施标点真实点击与关闭状态修复（2026-10-12）

## 真实根因
- `topics/infrastructure/topic.js` 的`selectEvent`在用户关闭“显示工程事件点”后选择事件档案时仍把`#filterWrap.hidden=false`，令关闭的地图图层其筛选控件无故重新出现；此问题是前次PR #82图层显隐修复剩余的同一状态漏口。
- 原有自动化只点击`#eventList button`，没有真正点击`L.marker`在地图上的`infra-marker-icon`，无法保障鼠标命中与相机保持。

## 修复/验收
- `selectEvent`令`filterWrap.hidden=!state.showEvents`，事件目录仍可在标点关闭时阅读；用户勾选标点时才出现筛选器。
- 新增只读`GermanInfrastructureQA`，供桌面1460/移动390浏览器读取真实Map/State/marker层和选中状态。图层业务数据未改变。
- 在现有Chromium流程：显式选择图林根→显示工程事件点→真实鼠标点击工程 marker→打开所选工程且中心/zoom不变；之后关标点、阅读列表档案→marker仍为0、筛选器仍隐藏；再手动打开复选框→筛选器出现。

## 保护与后续
- 保留16州、22条精选事件、县级桥梁研究候选、非官方试验指数、DIN/TLI等指标和全部外链，不加入首页警告段落。
- 原外部数据自动抓取及定时刷新持续关闭，只运行CI/部署。
- 下一轮重点真实点击州多边形与标记的叠层命中（尤其标记附近）、工业开启点位时的县Canvas点击、住房反复切换指标后的AGS和图例一致。