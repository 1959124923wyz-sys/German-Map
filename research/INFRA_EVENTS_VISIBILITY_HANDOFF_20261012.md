# 维护5｜基础设施事件阅读不能重开已关闭标点（2026-10-12）

## 自主排查：根因
- topics/infrastructure/topic.js 的 selectEvent(id) 原来不检查用户是否勾选“显示工程事件点”，直接把 state.showEvents 和 showEvents checkbox 改成 true。
- 当用户在地图中手动关闭事件点而只阅读事件目录时，选择单条项目会将开关重新打开，形成事件点显隐状态与实际图层不一致。这类问题曾在环保地图PR #76出现。

## 本次修复
- selectEvent(id)只设置所选州及项目、更新州资料室/项目详细来源，保留当前event overlay可见性。
- 唯一负责显隐控制的仍是showEvents复选框change监听及renderEvents。点地图marker本身须先打开图层，地图marker可点击时不会受到影响。
- topics/infrastructure/tests/smoke_browser.py现按桌面1460与手机390两套完整流程：选州→打开工程点→打开详情→关闭工程点→仍可点清单读详情→复选框始终不变/地图标点仍为0→手动再次启用。
- 未修改数据：16州试验模型、22个精选工程记录、400县桥梁候选记录、各年份与DIN/TLI量纲和来源不变。

## 发布标准
- PR须通过 .github/workflows/three-topics-pr-check.yml 的source-check与全部行业/基建/住房真Chromium回归，并完成Pages发布后才算网站上线。
- PR #74停用的所有自动外部搜索、数据刷新仍继续关闭；新测试只读取Git已归档数据。

## 下一轮建议
- 实际click穿透优先覆盖工业 marker图层开启后县/州polygon、住房 bringToFront 的州界与县详情、基建事件marker 与州选择；也要看390px详情面板对地图的遮挡。
- 继续完善不随用户意图擅自重置已关闭的图层、已选择指标、正在阅读的资料室tab等状态契约。