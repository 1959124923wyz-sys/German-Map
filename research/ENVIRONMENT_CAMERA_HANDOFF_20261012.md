# 维护5｜环保地图普通阅读与主动定位分离（2026-10-12）

## 证实的原因
维护4已经确立了点击州、县、企业/事件资料时不应自动挪动地图的共同规则。环保主题 `topics/environment/topic.js` 中地图普通点击州与 `#envStateJump` 共用 `selectState`，其中无条件执行 `map.fitBounds`；记录列表 `#entries`、地点排名 `#rankList`、联邦州档案 `#envStateList` 使用 `selectRecord(id,true)`，导致只想读证据时地图自动跳向坐标。

## 修复
- `selectState(iso,{locate=false})` 默认只展示资料；州下拉菜单显式定位，另提供“定位本州”按钮。
- `#entries`、`#rankList` 和 `#envStateList` 的普通选择不再主动相机跳转；记录详情新增“定位地点”按钮。真正点击地图点位也不会自动移动镜头。
- 已有数据与调查源完整保留：154条研究记录、类型与状态、独立事件坐标精度与时间、73条明确州归属、16州GIS、是否显示标记的开关。
- 延伸 `topics/environment/tests/smoke_environment.py`：州资料普通选择、事件列表普通选择时地图中心与缩放不变；显式州和事件定位则可移动，原有桌面1440/手机390 Chromium数据/页面检查保留。

## 提醒
- 标注为设施/市镇/机构的点位仍为来源允许的参考精度；“定位地点”仅前往记录的参考点，不意味着精确坐标或实际影响区域。
- 合并前必须 `.github/workflows/environment-map-smoke.yml` 及跨专题视觉测试全部绿灯；本PR不运行任何自动外部数据采集，符合最新的 manual-only workflow 政策。
