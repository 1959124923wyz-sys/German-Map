#!/usr/bin/env python3
"""Diagnose seam alignment between official city detail and national county polygons."""
import json, math
from collections import Counter
from pathlib import Path
from shapely.geometry import shape
from shapely.ops import unary_union,transform
from pyproj import Transformer

ROOT=Path(__file__).resolve().parents[1]
coarse=json.loads((ROOT/"data/germany-counties.geojson").read_text())
berlin=json.loads((ROOT/"data/berlin_violent_2025.geojson").read_text())
munich=json.loads((ROOT/"data/munich_local_2025.geojson").read_text())
print("COUNTY meta",str(coarse.get('meta'))[:1500],"features",len(coarse["features"]))
for f in coarse["features"][:4]:print("COUNTY sample",f.get("id"),str(f.get("properties"))[:450])
for f in coarse["features"]:
 p=f.get("properties") or {}
 s=str(p).lower()
 if "berlin" in s or "münchen" in s or "muenchen" in s:
  geom=shape(f["geometry"])
  print("CITY COUNTY",f.get("id"),p,"bbox",geom.bounds,"area",round(geom.area,6))
for cityname,fs in [("Berlin",berlin["features"]),("München",munich["features"])]:
 projector=Transformer.from_crs("EPSG:4326","EPSG:3035",always_xy=True).transform
 polys=[transform(projector,shape(f["geometry"])) for f in fs]
 areas=[x.area for x in polys]
 invalid=[(i,x.is_valid) for i,x in enumerate(polys) if not x.is_valid]
 try:whole=unary_union(polys)
 except Exception as e:
  print(cityname,"UNION ERROR",repr(e))
  whole=unary_union([p.buffer(0) for p in polys])
 print("CITY",cityname,"count",len(fs),"valid",len(fs)-len(invalid),"invalid",invalid[:10],"totalSqkm",round(sum(areas)/1e6,3),"unionSqkm",round(whole.area/1e6,3),"overlapSqkm",round((sum(areas)-whole.area)/1e6,3),"bbox",whole.bounds)
 ctr=Counter(str(f.get("properties",{}).get("bZR")) for f in fs)
 print("BZR counts",ctr.most_common(4))
 target=[]
 for f in coarse["features"]:
  prop=f.get("properties") or {}
  ss=str(prop).lower()
  name=cityname.lower()
  if (cityname=="Berlin" and "berlin" in ss) or (cityname=="München" and ("münchen" in ss or "muenchen" in ss)):
    target.append((f,transform(projector,shape(f["geometry"]))))
 print("TARGET COUNTIES",cityname,[(f.get("id"),p.get("properties",{}).get("name"),round(g.area/1e6,3)) for f,g in target])
 for f,g in target:
  if cityname=="München" and g.area>400e6:continue
  intr=g.intersection(whole).area
  missing=g.difference(whole).area
  extra=whole.difference(g).area
  print("MATCH",cityname,"target",f.get("id"),"inside%",round(100*intr/g.area,3),"missingSqkm",round(missing/1e6,4),"extraSqkm",round(extra/1e6,4),"hausdorff(m)",round(g.hausdorff_distance(whole),1))
  gaps=g.difference(whole)
  extras=whole.difference(g)
  for name,x in [("gaps",gaps),("extras",extras)]:
   poly=list(x.geoms) if hasattr(x,"geoms") else [x]
   poly=sorted([p for p in poly if p.geom_type in ("Polygon","MultiPolygon")],key=lambda x:-x.area)
   print(name,"components",len(poly),"topareasSqkm",[round(a.area/1e6,5) for a in poly[:8]],"worstShapeBounds",[p.bounds for p in poly[:2]])
