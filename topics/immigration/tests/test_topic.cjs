'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const script = fs.readFileSync(path.join(root, 'topic.js'), 'utf8');
const azr = JSON.parse(fs.readFileSync(path.join(root, 'data/state-return-obligations-2025.json'), 'utf8'));
const deport = JSON.parse(fs.readFileSync(path.join(root, 'data/state-deportations-2025.json'), 'utf8'));

class Element {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.listeners = new Map();
    this.attrs = new Map();
    this.style = {};
    this.value = '';
    this.textContent = '';
    this.parent = null;
    this.removed = false;
  }
  append(...children) {
    for (const child of children) {
      child.parent = this;
      this.children.push(child);
      if (this.tag === 'select' && child.tag === 'option' && !this.value) this.value = child.value;
    }
  }
  replaceChildren(...children) {
    for (const child of this.children) child.parent = null;
    this.children = [];
    this.textContent = '';
    this.append(...children);
  }
  setAttribute(name, value) { this.attrs.set(name, value); }
  addEventListener(name, callback) {
    if (!this.listeners.has(name)) this.listeners.set(name, new Set());
    this.listeners.get(name).add(callback);
  }
  removeEventListener(name, callback) {
    this.listeners.get(name)?.delete(callback);
  }
  emit(name) { for (const fn of this.listeners.get(name) ?? []) fn({target:this}); }
  remove() {
    this.removed = true;
    if (this.parent) this.parent.children = this.parent.children.filter(x=>x!==this);
  }
  descendants() { return [this, ...this.children.flatMap(c => c.descendants())]; }
}
function setup({corruptAzr=false,missingState=false}={}) {
  const paneByName = new Map();
  const layers = new Set();
  const map = {
    layers,
    getPane: name => paneByName.get(name),
    createPane(name) {
      const pane = {style:{}};
      paneByName.set(name, pane);
      return pane;
    },
    hasLayer: layer => layers.has(layer),
    removeLayer: layer => layers.delete(layer),
    on() { throw Error('Topic must not bind host map events'); },
    off() { throw Error('Topic must not alter host map events'); }
  };
  const leaflet = {
    calls: [],
    geoJSON(geo, options) {
      this.calls.push({geo, options});
      const own = {
        options,
        styles: [],
        addTo(mapInstance) {
          this.setStyle(options.style);
          mapInstance.layers.add(this);
          return this;
        },
        setStyle(fn) { this.styles = geo.features.map(f=>fn(f)); },
      };
      return own;
    }
  };
  const fakeDocument = {
    currentScript: {src:'https://example.invalid/topics/immigration/topic.js'},
    createElement: tag=>new Element(tag)
  };
  const fakeWindow = {};
  let fetches=[];
  const fakeFetch = async url => {
    fetches.push(url);
    if (url.endsWith('state-deportations-2025.json')) return {ok:true, json:async()=>deport};
    if (url.endsWith('state-return-obligations-2025.json')) {
      const d = corruptAzr ? {...azr,totals:{...azr.totals,total:0}} : azr;
      return {ok:true, json:async()=>d};
    }
    throw Error('Unexpected data URL '+url);
  };
  vm.runInNewContext(script, {window:fakeWindow,document:fakeDocument,
    fetch:fakeFetch,URL,L:leaflet,console}, {filename:'topic.js'});
  const topic = fakeWindow.GermanMapTopics.immigration;
  const all = azr.records.map(rec=>({type:'Feature',properties:{id:rec.iso}}));
  const geo = {type:'FeatureCollection',features:missingState?all.slice(0,-1):all};
  const container = new Element('aside');
  return {topic,map,leaflet,container,geo,paneByName,
    getFetches:()=>fetches, Element};
}
test('requires datasets and injected host map before activation', () => {
  const {topic,map,geo,container}=setup();
  assert.throws(()=>topic.activate({map,stateGeoJSON:geo,container}),/loadData/);
  assert.equal(map.layers.size,0);
  assert.equal(topic.getViewState().active,false);
});
test('loads both official sources once and draws four map modes', async () => {
  const {topic,map,geo,container,leaflet,paneByName,getFetches}=setup();
  await Promise.all([topic.loadData(),topic.loadData()]);
  assert.equal(getFetches().length,2,'concurrent load must deduplicate requests');
  await topic.loadData();
  assert.equal(getFetches().length,2,'validated sources must be cached');
  const hostLayer={owner:'host'};
  map.layers.add(hostLayer);
  let hostClicks=0;
  const context={map,stateGeoJSON:geo,container,onStateSelected:()=>hostClicks++};
  const result=topic.activate(context);
  assert.equal(result.matchedStates,16);
  assert.equal(result.reportedStates,16);
  assert.equal(map.layers.size,2);
  assert.equal(paneByName.get('immigrationDataPane').style.pointerEvents,'none');
  assert.equal(leaflet.calls[0].options.interactive,false);
  assert.equal(hostClicks,0,'initial render must not move host map');

  const ownedLayer=[...map.layers].find(x=>x!==hostLayer);
  const distinct=[];
  for(const metric of ['return_total','return_duldung','return_no_duldung','deportations']) {
    assert.equal(topic.selectMetric(metric),true);
    assert.equal(topic.getViewState().metric,metric);
    assert.equal(ownedLayer.styles.length,16);
    distinct.push(ownedLayer.styles.map(s=>s.fillColor).join(';'));
    assert.equal(hostClicks,0,'changing legend/metric never hijacks map navigation');
  }
  assert.ok(new Set(distinct).size>=3,'different official metrics change thematic shading');
  assert.equal(topic.selectMetric('fabricated'),false);
  assert.equal(topic.selectState('DE-HH'),true);
  assert.equal(topic.getViewState().state,'DE-HH');
  assert.equal(hostClicks,1,'explicit user-selected state can notify host');
  assert.equal(topic.selectState('UNKNOWN'),false);

  const rootElement=container.children[0];
  const controls=rootElement.descendants();
  topic.deactivate();
  topic.deactivate();
  assert.equal(map.layers.size,1);
  assert.ok(map.layers.has(hostLayer));
  assert.equal(container.children.length,0);
  for(const el of controls)
    for(const handlers of el.listeners.values())
      assert.equal(handlers.size,0,'all owned control listeners must be disposed');

  topic.activate(context);
  assert.equal(map.layers.size,2,'re-enter displays a single topic layer');
  assert.equal(hostClicks,1);
  topic.deactivate();
  assert.equal(map.layers.size,1);
  assert.equal(container.children.length,0);
});
test('missing geography is reported, never treated as count 0',async()=>{
  const {topic,map,geo,container}=setup({missingState:true});
  await topic.loadData();
  const answer=topic.activate({map,stateGeoJSON:geo,container});
  assert.equal(answer.matchedStates,15);
  assert.equal(answer.reportedStates,16);
  topic.deactivate();
});
test('rejects falsified official totals before drawing map',async()=>{
  const {topic,map,geo,container}=setup({corruptAzr:true});
  await assert.rejects(topic.loadData(),/AZR totals mismatch/);
  assert.throws(()=>topic.activate({map,stateGeoJSON:geo,container}),/loadData/);
  assert.equal(map.layers.size,0);
});
