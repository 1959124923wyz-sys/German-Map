/* German-Map semantic colors policy.
   Never infer "worse" solely from a metric's numeric direction.
   Meta controls only visual rank/legend; it never transforms source values. */
(() => {
 'use strict';
 const danger=Object.freeze(['#f5ead9','#f2d4ad','#eeb888','#e99a64','#df754e','#cb4d3d','#a52d37']);
 const neutral=Object.freeze(['#eff5f9','#d5e6ee','#b2d2e0','#87b7d0','#5c98b9','#37769b','#1b5278']);
 const kinds=Object.freeze({HIGH:'pressure-high',LOW:'pressure-low',NEUTRAL:'neutral',DIVERGING:'diverging',CATEGORIES:'categorical'});
 const registry=Object.freeze({
  housing:Object.freeze({
   asking_rent_2025_eur_m2:kinds.HIGH,
   completed_dwellings_new_residential_buildings_2023:kinds.NEUTRAL,
   sheltered_homeless_2025:kinds.NEUTRAL,
   existing_cold_rent_2022_eur_m2:kinds.HIGH,
   vacant_12mo_plus_of_vacant_2022_pct:kinds.NEUTRAL,
   vacant_available_3mo_of_vacant_2022_pct:kinds.NEUTRAL,
   vacancy_2022_pct:kinds.NEUTRAL,
   disposable_income_2023_keur_person:kinds.NEUTRAL,
   owner_occupier_2022_pct:kinds.NEUTRAL,
   living_area_2022_m2_person:kinds.LOW,
   homes_per_1000_people_2025:kinds.NEUTRAL,
   housing_stock_growth_2022_2025_pct:kinds.NEUTRAL,
   population_growth_2022_2025_pct:kinds.NEUTRAL,
   renewable_heat_new_2024_pct:kinds.NEUTRAL,
   renewable_heat_stock_2022_pct:kinds.NEUTRAL
  }),
  finance:Object.freeze({
   'balance-2025':kinds.DIVERGING,
   'core-2023':kinds.HIGH,
   'city-2024':kinds.HIGH,
   municipal_tax_capacity:kinds.NEUTRAL,
   municipal_debt:kinds.HIGH
  }),
  infrastructure:Object.freeze({experimental_state_score:kinds.LOW,
   bridge_elements_count:kinds.NEUTRAL,bridge_condition_rank:kinds.HIGH}),
  crime:Object.freeze({registered_violence_rate:kinds.HIGH,registered_theft_rate:kinds.HIGH}),
  drugs:Object.freeze({registered_drug_offence_rate:kinds.HIGH,wastewater_residue:kinds.NEUTRAL}),
  immigration:Object.freeze({AZR_registered_count:kinds.NEUTRAL,registered_share:kinds.NEUTRAL}),
  environment:Object.freeze({event_kind:kinds.CATEGORIES,facility_phase:kinds.CATEGORIES}),
  industry:Object.freeze({reported_shrinkage_event_count:kinds.HIGH,
   official_manufacturing_employment_change:kinds.LOW}),
  railway:Object.freeze({measured_delay_severity:kinds.HIGH,
   unmeasured_segments:kinds.NEUTRAL})
 });
 function get(topic,key){
  const result=registry[topic]?.[key];
  if(!result)throw new Error('Undeclared atlas color semantics: '+topic+'/'+key);
  return result;
 }
 function palette(topic,key){
  const semantic=get(topic,key);
  if(semantic===kinds.HIGH)return danger.slice();
  if(semantic===kinds.LOW)return danger.slice().reverse();
  if(semantic===kinds.NEUTRAL)return neutral.slice();
  throw new Error('Use a domain-specific divergent/category renderer for '+topic+'/'+key);
 }
 function legendText(topic,key){
  const s=get(topic,key);
  if(s===kinds.HIGH)return '由浅至深：问题相关指标升高';
  if(s===kinds.LOW)return '由深至浅：条件改善（低值需关注）';
  if(s===kinds.NEUTRAL)return '由浅至深：数值升高（不代表严重程度）';
  if(s===kinds.DIVERGING)return '赤字偏红，盈余偏绿；按正负值区分';
  return '颜色区分类别，不代表轻重排序';
 }
 function indexFor(value,breaks){
  if(typeof value!=='number'||!Number.isFinite(value))return -1;
  let i=0;while(i<breaks.length&&value>breaks[i])i++;
  return i;
 }
 window.AtlasColorSemantics=Object.freeze({kinds,registry,get,palette,legendText,indexFor,
  palettes:Object.freeze({danger,neutral})});
})();
