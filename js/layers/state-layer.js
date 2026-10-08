(() => {
  'use strict';

  function create({
    map, getStateGeo, getStatePanel, tooltipHtml, onChange,
  }) {
    let layer = null;
    // Reuse one renderer across zooms. Creating a new SVG renderer for every
    // zoomend would leak empty DOM containers and eventually hinder clicks.
    const stateRenderer = L.svg({pane:'statePane',padding:.2});

    function style(feature) {
      const selected = feature?.properties?.name === getStatePanel()?.selectedName;
      return {
        pane:'statePane',color:selected?'#ffffff':'#20384b',
        weight:selected?3.1:2,opacity:selected?1:.98,
        fillColor:'#dce7ee',fillOpacity:selected?.045:.012,
      };
    }

    function render() {
      if (layer) { map.removeLayer(layer); layer = null; }
      const geo = getStateGeo();
      if (!geo || map.getZoom() >= 7.5) return null;
      // If the state outlines are visible, state selection must remain
      // interactive. The old <=7.15 threshold produced dead polygons at
      // zoom 7.15–7.5, especially after fitBounds/close cycles.
      const interactive = true;
      // Leaflet's default preferCanvas renderer missed genuine pointer clicks
      // on nearly transparent state fills. A dedicated SVG renderer gives
      // every state's interior its own browser hit target.
      layer = L.geoJSON(geo,{
        pane:'statePane',renderer:stateRenderer,style,interactive,
        onEachFeature:(feature,target)=>{
          if (!interactive) return;
          target.bindTooltip(()=>tooltipHtml(feature),{sticky:true,direction:'top',className:'state-tip'});
          target.on('mouseover',()=>{
            if(feature.properties?.name!==getStatePanel()?.selectedName)
              target.setStyle({color:'#f4fbff',weight:2.65,fillOpacity:.055});
          });
          target.on('mouseout',()=>layer?.resetStyle(target));
          target.on('click',()=>{
            getStatePanel().select(feature);
            layer.eachLayer(item=>layer.resetStyle(item));
            target.setStyle(style(feature));
            onChange?.(feature);
            // Never auto-zoom on state click: it used to place the map near the
            // interaction cutoff and trap users after closing the overview.
            // A state drawer is an overlay, not a map navigation command.
          });
        }
      }).addTo(map);
      return layer;
    }

    return Object.freeze({render,style,get layer(){return layer;}});
  }

  window.CrimeStateLayer=Object.freeze({create});
})();
