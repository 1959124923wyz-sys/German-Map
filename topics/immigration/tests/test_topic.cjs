'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const script = fs.readFileSync(path.join(root, 'topic.js'), 'utf8');
const official = JSON.parse(fs.readFileSync(
  path.join(root, 'data', 'state-deportations-2025.json'), 'utf8'));

class Element {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.listeners = new Map();
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
      if (this.tag === 'select' && child.tag === 'option' && !this.value)
        this.value = child.value;
    }
  }
  setAttribute(name, value) { this[name] = value; }
  addEventListener(name, callback) { this.listeners.set(name, callback); }
  removeEventListener(name, callback) {
    if (this.listeners.get(name) === callback) this.listeners.delete(name);
  }
  remove() {
    this.removed = true;
    if (this.parent) this.parent.children = this.parent.children.filter(x => x !== this);
  }
}

function setup() {
  const paneByName = new Map();
  const layers = new Set();
  const map = {
    layers,
    getPane: name => paneByName.get(name),
    createPane(name) {
      const pane = {style: {}};
      paneByName.set(name, pane);
      return pane;
    },
    hasLayer: layer => layers.has(layer),
    removeLayer: layer => layers.delete(layer),
  };
  const leaflet = {
    calls: [],
    geoJSON(geo, options) {
      this.calls.push({geo, options});
      return {
        addTo(mapInstance) {
          geo.features.forEach(feature => options.style(feature));
          mapInstance.layers.add(this);
          return this;
        }
      };
    },
  };
  const fakeDocument = {
    currentScript: {src: 'https://example.invalid/topics/immigration/topic.js'},
    createElement: name => new Element(name),
  };
  const fakeWindow = {};
  let fetches = 0;
  const fakeFetch = async (url) => {
    assert.match(url, /state-deportations-2025\.json$/);
    fetches++;
    return {ok: true, json: async () => official};
  };
  vm.runInNewContext(script, {
    window: fakeWindow, document: fakeDocument, fetch: fakeFetch,
    URL, L: leaflet, console,
  }, {filename: 'topic.js'});
  const topic = fakeWindow.GermanMapTopics.immigration;
  const geo = {type: 'FeatureCollection', features:
    official.records.map(rec => ({type: 'Feature', properties:{id:rec.iso}}))};
  const container = new Element('aside');
  return {map, topic, geo, container, leaflet, paneByName, fetchCount: () => fetches};
}

test('module requires loadData and a host map before activation', () => {
  const {topic, map, geo, container} = setup();
  assert.throws(() => topic.activate({map, stateGeoJSON:geo, container}), /loadData/);
  assert.equal(map.layers.size, 0);
});

test('load activate deactivate activate cleans only its own layer and handlers', async () => {
  const {topic, map, geo, container, leaflet, paneByName, fetchCount} = setup();
  assert.equal(topic.id, 'immigration');
  await topic.loadData();
  await topic.loadData();
  assert.equal(fetchCount(), 1, 'caches validated dataset');
  const otherLayer = {owner: 'main'};
  map.layers.add(otherLayer);

  const context = {map, stateGeoJSON:geo, container};
  const result = topic.activate(context);
  assert.equal(result.matchedStates, 16);
  assert.equal(result.reportedStates, 16);
  assert.equal(map.layers.size, 2);
  assert.equal(leaflet.calls[0].options.interactive, false);
  assert.equal(paneByName.get('immigrationDataPane').style.pointerEvents, 'none');
  assert.equal(container.children.length, 1);

  topic.deactivate();
  topic.deactivate(); // idempotence
  assert.equal(map.layers.size, 1);
  assert.ok(map.layers.has(otherLayer), 'host-owned layer untouched');
  assert.equal(container.children.length, 0);

  topic.activate(context);
  assert.equal(map.layers.size, 2);
  assert.equal(container.children.length, 1);
  topic.deactivate();
  assert.equal(map.layers.size, 1);
  assert.equal(container.children.length, 0);
  assert.equal(leaflet.calls.length, 2);
});
