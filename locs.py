"""One-off: turn the VEC suburb/postcode file (data/src/electors_aug2026.xlsx) into data/localities.json."""
import zipfile,re,json,xml.etree.ElementTree as ET
z=zipfile.ZipFile('src/electors_aug2026.xlsx')
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
ss=[''.join(t.text or '' for t in si.iter('{%s}t'%ns['m'])) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
agg={}
for r in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).iter('{%s}row'%ns['m']):
    row={}
    for c in r.findall('m:c',ns):
        col=re.match(r'[A-Z]+',c.get('r')).group(0); v=c.find('m:v',ns)
        if v is not None: row[col]=ss[int(v.text)] if c.get('t')=='s' else v.text
    if not re.match(r'^\d{4}$',row.get('B','')): continue
    try: n=int(row['K'])
    except: continue
    key=(row['A'].strip(),row['B'])
    d=agg.setdefault(key,{})
    d[row['F'].strip()]=d.get(row['F'].strip(),0)+n
out=[[k[0],k[1],sorted([[a,b] for a,b in v.items()],key=lambda x:-x[1])] for k,v in sorted(agg.items())]
json.dump(out,open('localities.json','w'),separators=(',',':'))
print(len(out),'localities')
import os;print(os.path.getsize('localities.json'),'bytes')
print([x for x in out if x[0] in('Brunswick','Geelong','Mildura')][:4])
