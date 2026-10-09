(() => {
  'use strict';
  // Reference coordinates for major German city centres; display labels only.
  // No statistics are derived from these approximate points.
  const CITIES = [
    ['Berlin',52.5200,13.4050,1], ['Hamburg',53.5511,9.9937,1],
    ['München',48.1374,11.5755,1], ['Köln',50.9375,6.9603,1],
    ['Frankfurt am Main',50.1109,8.6821,1], ['Stuttgart',48.7758,9.1829,1],
    ['Düsseldorf',51.2277,6.7735,1], ['Dortmund',51.5136,7.4653,1],
    ['Bremen',53.0793,8.8017,1], ['Hannover',52.3759,9.7320,1],
    ['Leipzig',51.3397,12.3731,1], ['Dresden',51.0504,13.7373,1],
    ['Nürnberg',49.4521,11.0767,1], ['Essen',51.4566,7.0123,1],
    ['Duisburg',51.4344,6.7623,2], ['Bochum',51.4818,7.2162,2],
    ['Wuppertal',51.2562,7.1508,2], ['Bielefeld',52.0302,8.5325,2],
    ['Bonn',50.7374,7.0982,2], ['Münster',51.9607,7.6261,2],
    ['Karlsruhe',49.0069,8.4037,2], ['Mannheim',49.4875,8.4660,2],
    ['Augsburg',48.3705,10.8978,2], ['Wiesbaden',50.0782,8.2398,2],
    ['Aachen',50.7753,6.0839,2], ['Braunschweig',52.2689,10.5268,2],
    ['Chemnitz',50.8278,12.9214,2], ['Kiel',54.3233,10.1228,2],
    ['Magdeburg',52.1205,11.6276,2], ['Freiburg',47.9990,7.8421,2],
    ['Mainz',49.9929,8.2473,2], ['Lübeck',53.8655,10.6866,2],
    ['Erfurt',50.9848,11.0299,2], ['Rostock',54.0924,12.0991,2],
    ['Potsdam',52.4009,13.0591,2], ['Kassel',51.3127,9.4797,2],
    ['Halle (Saale)',51.4825,11.9705,2], ['Heidelberg',49.3988,8.6724,3],
    ['Saarbrücken',49.2402,7.0050,3], ['Paderborn',51.7189,8.7575,3],
    ['Ingolstadt',48.7665,11.4258,3], ['Regensburg',49.0134,12.1016,3],
    ['Ulm',48.4011,9.9876,3], ['Osnabrück',52.2799,8.0472,3],
    ['Koblenz',50.3569,7.5889,3], ['Göttingen',51.5413,9.9158,3]
  ];
  function create(map, options = {}) {
    if (!map || !window.L) throw new Error('Leaflet map required');
    const paneName = options.paneName || 'majorCityLabels';
    if (!map.getPane(paneName)) map.createPane(paneName);
    const pane = map.getPane(paneName);
    pane.style.zIndex = String(options.zIndex || 440);
    pane.style.pointerEvents = 'none';
    pane.setAttribute('aria-hidden', 'true');
    const group = L.layerGroup().addTo(map);
    let active = true;
    function draw() {
      group.clearLayers();
      if (!active) return;
      const zoom = map.getZoom();
      const size = map.getSize();
      const bounds = map.getBounds().pad(.04);
      const occupied = [];
      const spacing = zoom < 7 ? 17 : 12;
      // More major cities at progressively finer scales, but never an unreadable wall of text.
      const maxTier = zoom < 6.2 ? 1 : zoom < 7.25 ? 2 : 3;
      for (const [name,lat,lon,tier] of CITIES) {
        if (tier > maxTier || !bounds.contains([lat,lon])) continue;
        const p = map.latLngToContainerPoint([lat,lon]);
        const title = window.GermanPlaceNames?.translate(name) || name;
        const visualUnits = [...title].reduce((sum, ch) => sum + (/[^\x00-\xff]/.test(ch) ? 1.55 : 1),0);
        const width = Math.min(142, Math.max(41,visualUnits * (zoom < 7 ? 7.0 : 7.7) + 14));
        const height = 24;
        const rect = {l:p.x-width/2-spacing,r:p.x+width/2+spacing,
          t:p.y-height/2-spacing,b:p.y+height/2+spacing};
        if (rect.r < 0 || rect.l > size.x || rect.b < 0 || rect.t > size.y) continue;
        if (occupied.some(o => !(rect.r < o.l || rect.l > o.r || rect.b < o.t || rect.t > o.b))) continue;
        occupied.push(rect);
        const node=document.createElement('span');
        node.className='crime-city-label';
        node.textContent=title;
        node.dataset.germanName=name;
        const icon=L.divIcon({
          className:'crime-city-label-icon',
          html:node.outerHTML,
          iconSize:[1,1],iconAnchor:[0,0]
        });
        L.marker([lat,lon],{icon,pane:paneName,interactive:false,keyboard:false,zIndexOffset:0}).addTo(group);
      }
    }
    map.on('zoomend moveend resize',draw);
    draw();
    return Object.freeze({
      draw,
      setVisible(visible){active=Boolean(visible);draw();},
      destroy(){map.off('zoomend moveend resize',draw);group.clearLayers();map.removeLayer(group);}
    });
  }
  window.CrimeCityLabels=Object.freeze({create});
})();