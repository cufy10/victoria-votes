import json,re
M=json.load(open('model_out.json'))
geo=json.load(open('districts.geojson'))
ct=open('cands.txt').read().split('==Legislative Assembly==')[0]
ret=set()
for m in re.finditer(r'MLA \(\[\[([^\]]+)\]\]\)',ct):
    n=m.group(1).split('|')[-1].replace('Electoral district of ','').replace(' (Victoria)','').strip()
    ret.add(n)
print('retiring',sorted(ret))
SUF={'TR':'Republican MAGA','Cannabis':'Legalise Cannabis','West':'The West Party','ACP':'Australian Citizens Party','SV-VCP':'Freedom Party','SFF':'Shooters, Fishers and Farmers','AD':'Australian Democrats','LBT':'Libertarian','Climate':'Climate','Ind':'Independent','FF':'Family First','AJP':'Animal Justice','DLP':'Democratic Labour','SA':'Socialist Alliance','LDP':'Liberal Democrats','LCP':'Legalise Cannabis','LC':'Legalise Cannabis','FP':'Freedom Party','SF':'Sustainable Australia','CA':'Citizens Party','TNL':'Trumpet of Patriots','TOP':'Trumpet of Patriots','Fusion':'Fusion','Aus':'Australian Values','AC':'Australian Christians'}
unk=set()
def parse_other(o):
    o=o.replace("'",'').replace('}','').strip()
    m=re.match(r'^(.*?)\s*\(([^)]+)\)\s*$',o)
    if not m: unk.add('NOSUF:'+o); return {'name':o,'party':'Other'}
    p=m.group(2).strip()
    if p not in SUF: unk.add(p)
    return {'name':m.group(1).strip(),'party':SUF.get(p,p)}
seats={}
for n,s in M['seats'].items():
    c=s['cands']
    def one(k):
        v=c.get(k)
        if not v: return None
        d={'name':v['name']}
        if v.get('inc'): d['inc']=1
        if v.get('sub'): d['sub']=v['sub']
        return d
    seats[n]={k:s[k] for k in ('name','region','cls','cx','cy','held','heldCode','member','margin','p22','alp2pp22','prob','fav','favP','proj','finalTwo','finalTwoP','seatPoll')}
    seats[n]['cands']={k:one(k) for k in ('ALP','COA','GRN','ONP','VS')}
    seats[n]['others']=[parse_other(o) for o in s['others']]
    seats[n]['retiring']=n in ret
seats['Hawthorn']['seatPoll']={'hist':True,'text':'Freshwater Strategy, 14–16 Aug 2025 (n=1,147): Liberal 41% primary, Labor 55% to Liberal 45% two-party. Commissioned by Liberal members opposed to the Pesutto bailout. Pre-dates the candidate list.'}
print('unknown suffixes',unk)
# geometry keyed list (only name + coords)
for f in geo['features']: f['properties']={'name':f['properties']['name']}
out={'geo':geo,'seats':seats,'summary':M['summary'],'ranges':M['ranges'],'avg':M['avg'],'polls':M['polls']}
json.dump(out,open('app-data.json','w'),separators=(',',':'))
import os; print(os.path.getsize('app-data.json'))
from collections import Counter
print(Counter(s['cls'] for s in seats.values()))
print(sum(1 for s in seats.values() if s['retiring']))
