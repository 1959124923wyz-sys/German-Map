#!/usr/bin/env python3
"""Read-only official Kiel city data source probe (no map data publication).

Usage: python scripts/probe_kiel_sources.py
Probes municipal WFS capabilities, its advertised GeoJSON endpoint, and
the police's 2025 PKS annex. Failure is diagnostic, not a signal to invent data.
"""
from __future__ import annotations

import io
import json
import re
import xml.etree.ElementTree as ET

from pypdf import PdfReader

from city_build_common import download_bytes

GEO="https://ims.kiel.de/geodatenextern/services/Stadtplan/LHKielWmsWfs/MapServer/WFSServer"
PKS="https://www.schleswig-holstein.de/DE/landesregierung/ministerien-behoerden/POLIZEI/DasSindWir/PDen/Kiel/_downloads/pks/pks_pdkiel_2025.pdf?__blob=publicationFile&v=2"


def main():
    checks={}
    try:
        raw=download_bytes(GEO,{"service":"WFS","request":"GetCapabilities"},timeout=60)
        root=ET.fromstring(raw)
        features=[]
        for elem in root.iter():
            if elem.tag.split("}")[-1]=="FeatureType":
                features.extend((i.text or "") for i in elem if i.tag.split("}")[-1]=="Name")
        checks["wfs"]={"bytes":len(raw),"feature_names":features[:30]}
        print("[kiel-probe] WFS capabilities",json.dumps(checks["wfs"],ensure_ascii=False),flush=True)
    except Exception as e:
        checks["wfs"]={"error":str(e)}
        print("[kiel-probe] WFS capabilities ERROR",repr(e),flush=True)
    try:
        raw=download_bytes(GEO,{"outputFormat":"geoJSON","request":"GetFeature","service":"WFS","typeName":"Statistische_Stadtteile"},timeout=60)
        obj=json.loads(raw.decode("utf-8-sig"))
        fs=obj.get("features",[])
        checks["geojson"]={
            "bytes":len(raw),"count":len(fs),"properties_sample":(fs[0].get("properties") if fs else None),
            "geometry_type":(fs[0].get("geometry") or {}).get("type") if fs else None,
        }
        print("[kiel-probe] GeoJSON",json.dumps(checks["geojson"],ensure_ascii=False),flush=True)
    except Exception as e:
        checks["geojson"]={"error":str(e)}
        print("[kiel-probe] GeoJSON ERROR",repr(e),flush=True)
    # The GovData example omits the WFS namespace and returns an empty set.
    # Query advertised namespaced variants, but never publish without a real
    # feature count and verified municipality bounds.
    for variant,params in [
        ("qualified-1.0",{"service":"WFS","request":"GetFeature","version":"1.0.0",
                          "typeName":"lhkiel:Statistische_Stadtteile","outputFormat":"geoJSON"}),
        ("qualified-1.1",{"service":"WFS","request":"GetFeature","version":"1.1.0",
                          "typeName":"lhkiel:Statistische_Stadtteile","outputFormat":"geoJSON"}),
        ("qualified-2.0",{"service":"WFS","request":"GetFeature","version":"2.0.0",
                          "typeNames":"lhkiel:Statistische_Stadtteile","outputFormat":"geoJSON"}),
    ]:
        try:
            raw=download_bytes(GEO,params,timeout=60)
            obj=json.loads(raw.decode("utf-8-sig"))
            fs=obj.get("features",[])
            sample=(fs[0].get("properties") or {}) if fs else {}
            geom=(fs[0].get("geometry") or {}) if fs else {}
            vals={"bytes":len(raw),"count":len(fs),"sample_properties":sample,
                  "sample_geometry_type":geom.get("type")}
            checks[variant]=vals
            print("[kiel-probe]",variant,json.dumps(vals,ensure_ascii=False)[:2500],flush=True)
        except Exception as e:
            checks[variant]={"error":str(e)}
            print("[kiel-probe]",variant,"ERROR",repr(e),flush=True)
    # Municipal ArcGIS REST MapServer exposes an explicit polygon feature
    # layer at /38. This is more reliable than the broken WFS GeoJSON example.
    rest="https://ims.kiel.de/geodatenextern/rest/services/Stadtplan/LHKielWmsWfs/MapServer/38/query"
    try:
        raw=download_bytes(rest,{"where":"1=1","outFields":"*","outSR":"4326","f":"geojson"},timeout=70)
        obj=json.loads(raw.decode("utf-8-sig"))
        fs=obj.get("features",[])
        checks["rest-38"]={
            "bytes":len(raw),"count":len(fs),
            "names_sample":[(x.get("properties") or {}).get("Name") for x in fs[:15]],
            "codes_sample":[(x.get("properties") or {}).get("Nummer") for x in fs[:15]],
            "geometry_type":(fs[0].get("geometry") or {}).get("type") if fs else None,
            "first_point": (fs[0].get("geometry") or {}).get("coordinates",[None])[0] if fs else None
        }
        checks["rest-38"].pop("first_point",None)  # do not dump huge polygon in CI log
        print("[kiel-probe] ArcGIS REST layer 38",json.dumps(checks["rest-38"],ensure_ascii=False),flush=True)
    except Exception as e:
        checks["rest-38"]={"error":str(e)}
        print("[kiel-probe] ArcGIS REST ERROR",repr(e),flush=True)
    try:
        raw=download_bytes(PKS,timeout=75)
        reader=PdfReader(io.BytesIO(raw))
        text="\n".join((page.extract_text() or "") for page in reader.pages[-5:])
        for page_index in (30,31):
            snippet=(reader.pages[page_index].extract_text() or "")
            print("[kiel-probe] police-table-page",page_index+1,
                  repr(snippet[:7000]),flush=True)
        checks["pks"]={
            "bytes":len(raw),"pages":len(reader.pages),
            "has_stadtteile_table": "Kriminalitätsentwicklung in den Stadtteilen" in text,
            "has_gaarden_ost":"Gaarden-Ost" in text,
            "has_unknown_category":"Tatort unbekannt" in text,
            "table_excerpt":re.sub(r"\s+"," ",text[text.find("Kriminalitätsentwicklung in den Stadtteilen"):])[:350]
        }
        print("[kiel-probe] official police PDF",json.dumps(checks["pks"],ensure_ascii=False),flush=True)
    except Exception as e:
        checks["pks"]={"error":str(e)}
        print("[kiel-probe] PDF ERROR",repr(e),flush=True)
    print("[kiel-probe] RESULT",json.dumps(checks,ensure_ascii=False),flush=True)
    # Intentionally do not publish any crime polygons. The table currently
    # provides all-offense city-district totals, not the two mode metrics.
    if "error" in checks.get("pks",{}):
        raise SystemExit("Official Kiel PKS PDF could not be retrieved")


if __name__=="__main__":
    main()
