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
    try:
        raw=download_bytes(PKS,timeout=75)
        reader=PdfReader(io.BytesIO(raw))
        text="\n".join((page.extract_text() or "") for page in reader.pages[-5:])
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
