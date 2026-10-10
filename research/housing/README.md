# 德国住房危机地图｜研究原始资料与阶段交接

研究开始：2026-10-10。分支：`research/housing-crisis-20261010`。该分支只做住房数据研究、可复现采集和原型，不修改其他专题。此文档中的“已证实”指**官方来源/下载路径已核验**，不等于原始县级数据已下载并逐项核验。

## 官方住房数据集（第一批）
1. Deutschlandatlas HA26（官方主更新，2026-10-08）：https://deutschlandatlas.bund.de/service/daten-herunterladen/aktuelle-downloaddaten/aktuelle-downloaddateien
   - 指标字典 PDF：https://deutschlandatlas.bund.de/fileadmin/Downloaddateien/HA26/Indikatoren_Deutschlandatlas_HA26.pdf
   - 2024边界县级CSV：https://deutschlandatlas.bund.de/fileadmin/Downloaddateien/HA26/Deutschlandatlas_KRS1224_HA26.csv
   - 2022边界县级CSV：https://deutschlandatlas.bund.de/fileadmin/Downloaddateien/HA26/Deutschlandatlas_KRS1222_HA26.csv
   - 2022市镇联合体CSV：https://deutschlandatlas.bund.de/fileadmin/Downloaddateien/HA26/Deutschlandatlas_VBGEM1222_HA26.csv
   - 指标 **preis_miet**：2025挂牌/重复出租冷租金，欧元/㎡，2024县边界，来自BBSR及IDN ImmoDaten；HA26首次公布连续数值，不再只是区间级别。
   - 指标 **wohn_leer**：2022空置住宅占比，%，2022县边界，来自Zensus 2022（不含度假住宅）。
   - 指标 **wohn_eigen**：2022自住住房家庭占比，%，2022县边界。
   - 指标 **preis_miet_best**：2022存量租约净冷租金，欧元/㎡，2022**市镇联合体**边界；不是县级同口径现成序列，不直接把县名匹配作为县级原值。
   - 指标 **fl_wohn**：2022年人均居住面积，平方米，2024县边界。
   - 缺失占位 = -9999（指标字典中另有特殊 -99999），转换为 null；禁止补0。
2. Destatis GENESIS 31231-0020：2025年底县级住宅存量、居住面积、房间数：https://genesis.destatis.de/datenbank/online/statistic/31231/table/31231-0020
3. Destatis GENESIS 22971-0080：县级集中安置无住房人员，区县表：https://genesis.destatis.de/datenbank/online/statistic/22971/table/22971-0080 。覆盖完整性/隐私保护缺失值需核验；不代表所有无家可归者。
4. Neubauatlas（2018—2024年新建住宅、建设完工等）：https://www.statistikportal.de/de/karten/neubauatlas
5. Zensus2022 城市细分和100m网格：https://www.destatis.de/DE/Themen/Gesellschaft-Umwelt/Bevoelkerung/Zensus2022/_inhalt.html
6. Kiel GREIX 城市挂牌租金季度趋势：https://www.kielinstitut.de/de/forschung/forschungszentren/makrooekonomie/makrofinanzen/mietpreisindex/

## 合并与方法
- 项目既有 `data/germany-counties.geojson` 与 `data/germany-counties-display.geojson`（约402个AGS），`data/germany-states.geojson` 是唯一可复用底图。
- 原始2022、2024边界版本不同，必须以五位AGS精确匹配；未匹配编码列入审计，不按名称猜测，也不将缺失当0。地图涂色不应假称具有统一2026年区划。
- 强烈区分**挂牌租金**和**实际存量租金**、**全住房空置**和**市场可出租空置**、**正式集中安置无住房者**与全部无家可归者、**房屋数量**与**保障房数量**。
- 事件为非代表性样本，不可使用新闻频率构造“住房危机”排名；不创建跨口径合成指数。
- 地图 UI 参照 `topics/finance/` 简约左地图右侧栏、点击州县下钻、地图事件叠加默认关闭；地理详情有明确指标年份、来源、缺失状态。

## 数据保全
- 首批清单和方法保存后，再增加 `research/housing/build_*.py`、县级实值CSV、QA审计、网页JSON与阶段交接。
- 不从本地网络受限环境的下载失败推断上游失效。通过专门 GitHub Actions 环境联网采集时，必须校验记录完整性才落盘。
- 分支更新提交后在本文件或 `HANDOFF.md` 记录提交SHA、核验结果、风险与重启指令。
