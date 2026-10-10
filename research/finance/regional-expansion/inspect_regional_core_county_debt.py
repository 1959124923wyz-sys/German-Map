#!/usr/bin/env python3
"""Probe German Regionalstatistik 71327-01-05-4 official county core debt CSV.

DO NOT assume this core-budget-only dataset matches 2023/2024 integrated
debt including public companies. Persist hash/headers or failure status.
"""
from __future__ import annotations
import csv,hashlib,json,re,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parent
OUT=ROOT/'derived/regional_core_debt'
OUT.mkdir(parents=True,exist_ok=True)
RAW=Path('/tmp/finance08-regional-core')
RAW.mkdir(exist_ok=True)
URL='https://www.regionalstatistik.de/genesisws/downloader/00/tables/71327-01-05-4_00.csv'
def main():
 request=urllib.request.Request(URL,headers={
    'User-Agent':'Mozilla/5.0 GermanMapResearch/1.0','Accept':'text/csv,text/plain,*/*'})
 with urllib.request.urlopen(request,timeout=150) as r:
  body=r.read(60000001)
  content_type=r.headers.get('Content-Type','')
  status=r.status
 assert status==200 and 5000<len(body)<60000001,('unexpected download length',status,len(body),content_type)
 assert not body.lstrip()[:20].lower().startswith((b'<html',b'<!doctype',b'<?xml')),'Not CSV bytes'
 sha=hashlib.sha256(body).hexdigest()
 (RAW/'regional_71327-01-05-4_raw.csv').write_bytes(body)
 try:
  content=body.decode('utf-8-sig')
  enc='utf-8-sig'
 except UnicodeDecodeError:
  content=body.decode('cp1252')
  enc='cp1252'
 lines=content.splitlines()
 assert len(lines)>100,('too few official source lines',len(lines))
 top=lines[:30]
 widths={}
 for sep in (';',',','\t'):
  widths[sep]=sum(line.count(sep)>2 for line in lines[:120])
 sample_codes=sorted(set(re.findall(r'(?<!\d)(?:0[1-9]|1[0-6])\d{3}(?!\d)',content[:250000])))
 counts={str(y):len(re.findall(str(y),content)) for y in range(2021,2027)}
 audit={'source_url':URL,'source_identifier':'GENESIS_71327-01-05-4','http_status':status,
     'content_type':content_type,'source_raw_bytes':len(body),'raw_sha256':sha,
     'decoded_encoding':enc,'line_count':len(lines),'delimiter_indications':widths,
     'year_mentions_in_text':counts,'sample_ags5_candidates':sample_codes[:120],
     'source_line_samples':top,'source_obtained_verified_bytes':True,
     'parsed_county_value_rows':None,'not_audited_metric_unit':True,
     'statistical_scope':'core_budget_debt_only_not_integrated_local_debt',
     'status':'downloaded_for_schema_analysis_not_map_ready'}
 (OUT/'regional_71327_source_probe.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 print('SUCCESS 71327 county core debt downloaded',len(body),'bytes, lines',len(lines),'SHA256',sha,'ENC',enc)
 print('FIRST LINES',json.dumps(top[:6],ensure_ascii=False))
if __name__=='__main__':main()
