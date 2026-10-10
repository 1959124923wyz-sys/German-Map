#!/usr/bin/env python3
"""Inspect genuine 2023 integrated-municipal-debt XLSX, retain source hash and code-year audit.

Research only. Never interpret core-budget debt as integrated debt. No website writes.
A prior 2024 source XLSX is already normalized; this script does not assume 2023 has
the same worksheet numbers, column meanings or population denominator.
"""
from __future__ import annotations
import csv,hashlib,json,re,urllib.request,zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'derived/integrated_2023'
OUT.mkdir(parents=True,exist_ok=True)
TMP=Path('/tmp/finance08-2023')
TMP.mkdir(exist_ok=True)
URL='https://www.statistikportal.de/sites/default/files/2024-11/Integrierte_Schulden_der_Gemeinden_und_Gemeindeverbaende_2023_Tabellenband_0.xlsx'
ARCHIVE=TMP/'integrated_2023_original.xlsx'
PINNED_SHA256='af5b3e0ff66cd30f7566721028e57374bce2bffd1b1cb0fe3a870344b3bb53d0'
TAG='{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
CODE=re.compile(r'^\d{5}$|^\d{9}$|^\d{12}$')
SHEET=re.compile(r'^xl/worksheets/sheet(\d+)\.xml$')

def write_json(name,obj):
 (OUT/name).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

def get():
 req=urllib.request.Request(URL,headers={'User-Agent':'Mozilla/5.0 (GermanMap official finance research)'})
 with urllib.request.urlopen(req,timeout=120) as response:
  data=response.read(18_000_001)
 assert 4_000_000<len(data)<18_000_001,('unexpected 2023 official XLSX length',len(data))
 assert data[:2]==b'PK','source not OOXML workbook'
 sha=hashlib.sha256(data).hexdigest()
 assert sha==PINNED_SHA256,'2023 source checksum changed; re-inspect before loading'
 ARCHIVE.write_bytes(data)
 write_json('source_2023_download.json',{'url':URL,'bytes':len(data),'sha256':sha,'source_type':'original_official_xlsx','verified_zip':True,'reference_year':2023,'publication_date':'2024-11-27','retained_binary':'GitHub Actions artifact, not committed as Git blob','published_map':False})
 return zipfile.ZipFile(ARCHIVE)

def col_value(cell,strings):
 v=cell.find(TAG+'v')
 if v is not None and v.text is not None:
  if cell.get('t')=='s':
   return strings[int(v.text)]
  return v.text
 inline=cell.find(TAG+'is')
 return ''.join(inline.itertext()) if inline is not None else ''

def scan(z,sheet,strings):
 samples=[]
 counts=Counter()
 numeric_rows=0
 top=[]
 with z.open(sheet) as f:
  for _,row in ET.iterparse(f,events=('end',)):
   if row.tag!=TAG+'row':continue
   cells={}
   for c in row.findall(TAG+'c'):
    ref=c.attrib.get('r','')
    match=re.match('[A-Z]+',ref)
    if match and match.group() in {'A','B','C','D','E','G','J','L','Q'}:
     cells[match.group()]=col_value(c,strings)
   a=cells.get('A','').strip()
   if len(top)<7 and any(cells.values()):
    top.append({'row':row.get('r'),'A':cells.get('A','')[:90],'B':cells.get('B','')[:90],'C':cells.get('C','')[:90],'D':cells.get('D','')[:40],'E':cells.get('E','')[:40],'G':cells.get('G','')[:40]})
   if CODE.fullmatch(a):
    t={5:'county_administration',9:'joint_administration',12:'municipality'}[len(a)]
    counts[(t,a[:2])]+=1
    if cells.get('E','').strip():numeric_rows+=1
    if len(samples)<12:
     samples.append({'row':row.get('r'),'key':a,'name':cells.get('B','')[:100],'legal_form':cells.get('C','')[:70],'population_field':cells.get('D','')[:35],'total_field':cells.get('E','')[:35],'per_person_field':cells.get('G','')[:35]})
   row.clear()
 return {'sheet':sheet,'report_units':sum(counts.values()),'numeric_E_rows':numeric_rows,
         'by_type_state':[{'type':t,'state':s,'count':n} for (t,s),n in sorted(counts.items())],
         'top_nonempty_rows':top,'first_report_units':samples}

def main():
 with get() as z:
  names=z.namelist()
  assert 'xl/workbook.xml' in names,'corrupted workbook'
  strings=[]
  if 'xl/sharedStrings.xml' in names:
   root=ET.fromstring(z.read('xl/sharedStrings.xml'))
   strings=[''.join(si.itertext()) for si in root.findall(TAG+'si')]
  sheets=sorted((n for n in names if SHEET.fullmatch(n)),key=lambda s:int(SHEET.fullmatch(s).group(1)))
  assert len(sheets)>5 and len(strings)>1000,('unexpected workbook layout',len(sheets),len(strings))
  details=[scan(z,name,strings) for name in sheets]
  populated=[x for x in details if x['report_units']>0]
  tally=Counter()
  for d in populated:
   for r in d['by_type_state']:tally[r['type']]+=r['count']
  assert len(populated)==13,'Expected 13 non-city states, including small Saarland tab'
  assert sum(tally.values())==11896,('unexpected official 2023 unit count',sum(tally.values()))
  audit={'reference_year':2023,'sheet_count':len(sheets),'shared_strings':len(strings),
         'populated_sheets':len(populated),'source_url':URL,'report_units_candidate_total':sum(tally.values()),
         'candidate_unit_types':dict(tally),'status':'workbook_columns_inspected_not_harmonized',
         'warning':'Do not copy 2024 workbook column mapping into 2023 until sheet headers and denominator separately verified',
         'sheet_inspection':details}
  write_json('workbook_2023_structure_audit.json',audit)
  assert tally=={'county_administration':294,'joint_administration':831,'municipality':10771},tally
  print('PASS: 2023 official XLSX inspected, candidate reporting rows',sum(tally.values()),'sheets',len(sheets))
if __name__=='__main__':main()
