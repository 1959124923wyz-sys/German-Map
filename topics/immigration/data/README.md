# 2025 annual deportations by executing authority

- Dataset: `state-deportations-2025.json`
- Original: Bundestag Drucksache 21/4403, answer to Question 2, PDF page 4: https://dserver.bundestag.de/btd/21/044/2104403.pdf
- Source of figures: *Polizeiliche Eingangsstatistik der Bundespolizei*.
- Date of release: 2026-02-26; reference period: 2025 calendar year.
- Geographic unit: 16 state **executing authorities**; the Bundespolizei is a separate national authority, not a state.
- Counts: 22,174 reported under the states + 613 reported under the federal police = 22,787 nationally.
- State `iso` IDs match the existing `data/germany-states.geojson` `properties.id`. State `ags` is the 2-digit German administrative state code; state boundaries are not copied or changed here.
- Coverage: all 16 states; no missing state rows in the source table. Do **not** interpret numbers as state residents subject to deportation, number of undocumented migrants, or prevalence/risk.
- Comparability: State figures are absolute actions by the responsible authority; no rates or population denominators are included. These data cannot support an inference about undocumented population distributions.
- No estimates or values for smaller administrative districts have been added.

- **AZR 2025年12月31日16州离境义务**：见 [state-return-obligations-2025.md](state-return-obligations-2025.md)，州级绝对人数；并非违法犯罪发生率。
