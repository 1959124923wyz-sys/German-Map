# 维护5｜住房县界真实鼠标验收（2026-10-12）

## 审计动机
- 原住房浏览器自动化只点击右栏州县列表及档案；地图Leaflet的县Polygon和置顶的州界几何没有真实mouse.click覆盖。
- `topics/housing/topic.js` 创建400县交互SVG，再执行`stateLayer.bringToFront()`，州外边框置顶而设置`interactive:false`。需要确认用户滚轮放大到县市后县点击是否落在正确AGS上。

## 本批验收
- 新增只读`GermanHousingResearch.getMap/getCountyLayer/getStateLayer`QA接口（不改界面），方便实地检查渲染层。
- 于1440/390真实Chromium：全国→地图手动进入zoom9→用几何containsPoint选真实县→检查`elementsFromPoint`包含可点县界→鼠标点击→县AGS与目标匹配→相机中心、zoom不变→点全国恢复。
- 保留其余15项指标、400县、GREIX城市样本、Zensus结构、地方档案与色阶正确方向；无数据继续灰色。

## 维护理念
- 优先测真实地图操作，尽量避免把大量显著的说明塞到用户首屏；研究来源仍在折叠文档中。
- 所有外部研究资料自动抓取和更新保持关闭。

## 下一批
- 基建16州与22工程标记并存时的真鼠标点击命中及事件列表保持；工业开启全部企业点时点位与县Polygon交互，重点底图边界附近。
- 统一将县/州点击、资料室关闭后再选、手机控制遮挡等行为纳入每题浏览器回归，按实际Bug优先修复。