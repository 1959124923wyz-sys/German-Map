# German-Map — 毒品问题专题 / Drug Topic

**工作分支：** `feature/drugs-topic`；与 `feature/immigration-topic` 并行。当前阶段不修改主站共享文件。

## 当前交付

- `index.html` / `topic.css`：可独立预览的2025年德国县级毒品案件地图。
- `topic.js`：可卸载Leaflet专题图层，提供 `GermanMapTopics.drugs.loadData / activate / deactivate`。
- `scripts/build_pks_drugs.py`：抓取全国约400个县、官方PKS转录镜像，按AGS校验16州。
- `scripts/validate_drugs.py`：严格数据检查，缺失不能填零。
- `data/pks_drugs_2025.json`：仅在成功构建后生成。
- `.github/workflows/drugs-topic-build.yml`：独立构建和审核，不部署主站。

## 来源与统计口径

县级指标 `Rauschgiftdelikte`：警方登记毒品违法案件（2025），案件数、每10万人案件数。

BKA官方县级T01数据：
https://data.gov.de/suche/daten/2025-polizeiliche-kriminalstatistik-t01-grundtabelle-kreise-ausgewahlte-straftaten-gruppen

自动抓取镜像：https://kriminalitaets-karte.de/kriminalitaet/

**透明性限制：** BKA文件下载端点在部分自动化环境返回403，因此采集器使用自称转录BKA县级表格的公共镜像；所有县均保留原始网址。尚未声称每一个数字与BKA直接下载文件完成交叉核对。未来应抽查原始CSV/XLSX。

**不可混淆：** 全国BKA `Rauschgiftkriminalität` 为164,991起，而县级镜像的 `Rauschgiftdelikte` 在法律罪名包含范围上可能不同。164,991是独立全国参考数，不应强行等同县级数据总和。

**大麻：** 没有把大麻排除。2024年4月1日部分合法化造成警察登记违法案件定义变化。合法使用不是违法案件，但不代表没有健康风险。消费状况应接入抽样调查和污水检测独立观察。

**解释限制：** 主动执法强度与法律定义会影响警方发现案件数，不能用分位色阶描述实际吸毒普遍程度。

## 本地构建

```bash
python -m pip install requests beautifulsoup4
python topics/drugs/scripts/build_pks_drugs.py
python topics/drugs/scripts/validate_drugs.py
node --check topics/drugs/topic.js
python -m http.server 8765
```

浏览 http://127.0.0.1:8765/topics/drugs/。

## 主站未来的接入契约

```js
const loaded = await GermanMapTopics.drugs.loadData({countyGeo, stateGeo});
await GermanMapTopics.drugs.activate({map, loaded, onSelection: selection => { /* 主站处理 */ }});
// 切换离开时：
GermanMapTopics.drugs.deactivate();
```

专题 activate 不缩放地图、不破坏公共地图实例、不修改公共状态；宿主负责隐藏其它专题图层及恢复自身。

## 后续扩展

1. 下载BKA官方原始县级表并抽样交叉核验。
2. 柏林／汉堡／不来梅官方毒品分区图层。
3. EUDA污水检测城市点与具体采样年份。
4. 毒品相关死亡、急性中毒、治疗需求。
5. 大麻／可卡因／冰毒／海洛因及交易、走私专项指标；只有可靠地区数据时才上线。
