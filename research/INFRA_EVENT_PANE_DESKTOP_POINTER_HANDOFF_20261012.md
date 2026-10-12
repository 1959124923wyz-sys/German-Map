# 维护6｜基建工程标记应在独立事件图层，桌面验证标记旁州界（2026-10-12）

## 主动排查
- `topics/infrastructure/topic.js`原创建了zIndex=530的`infraEventPane`，但实际`L.marker()`省略`pane`，因此工程标记在默认`markerPane`（zIndex=600）。自定义事件层名义存在，实际为空；这让工程点与州SVG（340）、城名层（440）的绘制顺序无法按设计审计。
- 历史Chromium已经验证能点工程marker，但没有在marker边缘外侧用真鼠标选州，无法分辨工程点命中区是否吞掉周边州。

## 最小修复
- 给22项工程的`L.marker`补`pane:'infraEventPane'`，让项目点真正进入工程专属图层。保留marker视觉状态/优先级、16州原polygon、项目来源和坐标。
- 原有1460桌面及390回归继续测工程marker真实点击；新增只在**桌面**运行的marker邻近实际像素测试：距离显示点24–45px中寻找真实位于州SVG且州polygon.containsPoint成立的点，触发page.mouse.click后断言州ISO匹配、原工程选择清空、地图中心缩放不变。
- QA还直接确认专属pane内存在项目标记且默认markerPane不再含工程标记。

## 后续
- 对事件点密集或贴近行政区边界的省份做更大样本指针点位抽检；分清真正命中marker（应打开事件）和marker外围命中州（应打开州）。
- 住房县Polygon与州边框交汇处真实点击、工业企业SVG标记半径外围县Canvas点击继续推进；仅做电脑端用户体验，不主动开发移动端。
- 不改图例、方法展示、源数据、不增加首页提醒；外部自动数据抓取继续关闭。