/* Station display labels only. Original DB identifiers/names stay unchanged. */
(()=>{
'use strict';
const city={
 'Berlin':'柏林','Hamburg':'汉堡','Hannover':'汉诺威','München':'慕尼黑',
 'Köln':'科隆','Frankfurt (Main)':'法兰克福','Frankfurt am Main':'法兰克福',
 'Düsseldorf':'杜塞尔多夫','Dortmund':'多特蒙德','Bremen':'不来梅',
 'Stuttgart':'斯图加特','Nürnberg':'纽伦堡','Leipzig':'莱比锡',
 'Dresden':'德累斯顿','Duisburg':'杜伊斯堡','Essen':'埃森',
 'Augsburg':'奥格斯堡','Kassel':'卡塞尔','Göttingen':'哥廷根',
 'Bielefeld':'比勒费尔德','Mannheim':'曼海姆','Bochum':'波鸿',
 'Darmstadt':'达姆施塔特','Erfurt':'埃尔福特','Fulda':'富尔达',
 'Heidelberg':'海德堡','Magdeburg':'马格德堡','Würzburg':'维尔茨堡',
 'Freiburg (Breisgau)':'弗赖堡','Freiburg':'弗赖堡','Halle (Saale)':'哈雷',
 'Halle':'哈雷','Karlsruhe':'卡尔斯鲁厄','Braunschweig':'不伦瑞克',
 'Osnabrück':'奥斯纳布吕克','Bonn':'波恩','Münster (Westf)':'明斯特',
 'Münster':'明斯特','Hagen':'哈根','Hamm (Westf)':'哈姆',
 'Hamm':'哈姆','Wuppertal':'伍珀塔尔','Gelsenkirchen':'盖尔森基兴',
 'Solingen':'索林根','Kiel':'基尔','Rostock':'罗斯托克',
 'Saarbrücken':'萨尔布吕肯','Mainz':'美因茨','Lübeck':'吕贝克',
 'Erlangen':'埃尔朗根','Ingolstadt':'因戈尔施塔特','Hanau':'哈瑙',
 'Celle':'策勒','Kempten (Allgäu)':'肯普滕','Aschaffenburg':'阿沙芬堡',
 'Koblenz':'科布伦茨','Ludwigslust':'路德维希斯卢斯特',
 'Lüneburg':'吕讷堡','Bitterfeld':'比特费尔德','Eisenach':'艾森纳赫',
 'Recklinghausen':'雷克林豪森','Marl':'马尔','Haltern am See':'哈尔滕湖畔',
 'Siegburg':'锡格堡','Wolfsburg':'沃尔夫斯堡','Hildesheim':'希尔德斯海姆',
 'Bad Kreuznach':'巴特克罗伊茨纳赫','Nidda':'尼达',
 'Neuss':'诺伊斯','Trier':'特里尔','Potsdam':'波茨坦',
 'Ulm':'乌尔姆','Regensburg':'雷根斯堡','Bamberg':'班贝格',
 'Passau':'帕绍','Flensburg':'弗伦斯堡','Schwerin':'什未林',
 'Paderborn':'帕德博恩','Oldenburg':'奥尔登堡','Wittenberg':'维滕贝格',
 'Chemnitz':'开姆尼茨','Jena':'耶拿','Gießen':'吉森'
};
const exact={
 'Berlin Hauptbahnhof':'柏林中央火车站',
 'Kassel-Wilhelmshöhe':'卡塞尔-威廉高地站',
 'Frankfurt am Main Flughafen Fernbahnhof':'法兰克福机场长途火车站',
 'Frankfurt (Main) Flughafen Fernbahnhof':'法兰克福机场长途火车站',
 'Köln Messe/Deutz':'科隆会展／道依茨站',
 'München Flughafen Terminal':'慕尼黑机场航站楼站',
 'Berlin Gesundbrunnen':'柏林健康泉站',
 'Berlin Südkreuz':'柏林南十字站',
 'Berlin Ostbahnhof':'柏林东站',
 'Berlin-Charlottenburg':'柏林夏洛滕堡站',
 'Berlin-Spandau':'柏林施潘道站',
 'Hamburg-Altona':'汉堡阿尔托纳站',
 'Hamburg Dammtor':'汉堡达姆托尔站',
 'Hamburg-Harburg':'汉堡哈尔堡站',
 'Frankfurt (Main) Süd':'法兰克福南站',
 'Düsseldorf Flughafen':'杜塞尔多夫机场站',
 'Siegburg/Bonn':'锡格堡／波恩站',
 'Recklinghausen Hbf':'雷克林豪森中央火车站',
 'Marl-Sinsen':'马尔-辛森站',
 'Haltern am See':'哈尔滕湖畔站'
};
const suffixes=[
 [/(?:\s+|-)Hauptbahnhof$/,'中央火车站'],
 [/(?:\s+|-)Hbf$/,'中央火车站'],
 [/\s+Flughafen$/,'机场站'],
 [/\s+Fernbahnhof$/,'长途火车站'],
 [/\s+Ostbahnhof$/,'东站'],
 [/\s+Südbahnhof$/,'南站'],
 [/\s+Nordbahnhof$/,'北站'],
 [/\s+Westbahnhof$/,'西站'],
 [/\s+Messe$/,'会展站'],
 [/\s+Süd$/,'南站'],
 [/\s+Nord$/,'北站'],
 [/\s+Ost$/,'东站'],
 [/\s+West$/,'西站'],
 [/\s+Bf$/,'火车站'],
 [/\s+Pbf$/,'客运站']
];
function localize(name){
 const original=String(name||'').trim();
 if(!original)return original;
 if(exact[original])return exact[original];
 for(const [suffix,translated] of suffixes){
  const hit=original.match(suffix);
  if(hit){
   const base=original.slice(0,-hit[0].length).trim();
   if(city[base])return city[base]+translated;
   const normal=window.GermanPlaceNames?.translate(base);
   if(normal&&normal!==base)return normal+translated;
  }
 }
 if(city[original])return city[original]+'站';
 return original;
}
window.GermanRailStations=Object.freeze({localize,city,exact});
})();