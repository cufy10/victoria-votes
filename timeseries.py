import json,math,subprocess,os,datetime
rows=json.load(open('rows_clean.json'))
codes=['ALP','LNP','GRN','ONP','IND','OTH']
# 1) run the model for every poll
for i,r in enumerate(rows):
    f=f'mo_row{i}.json'
    env=dict(os.environ,POLL=json.dumps([r['alp'],r['lnp'],r['grn'],r['onp']]),NSIM='1000',OUTF=f)
    subprocess.run(['python3','-I','model.py'],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=True)
MO=[json.load(open(f'mo_row{i}.json')) for i in range(len(rows))]
NAME={'lighthouse':('Lighthouse / Growth Intelligence Centre','Lighthouse'),'redbridge':('RedBridge / Accent','RedBridge'),'resolve':('Resolve Strategic','Resolve'),'demos':('DemosAU / Premier National','DemosAU'),'morgan':('Roy Morgan','Roy Morgan'),'newspoll':('Newspoll','Newspoll'),'oru':('Online Research Unit','Online Research Unit'),'freshwater':('Freshwater Strategy','Freshwater'),'yougov':('YouGov (MRP)','YouGov')}
def pick(T,maxage=60):
    best={}
    for i,r in enumerate(rows):
        d=datetime.date.fromisoformat(r['date']); age=(T-d).days
        if age<0 or age>maxage: continue
        if r['key'] not in best or d>datetime.date.fromisoformat(rows[best[r['key']]]['date']): best[r['key']]=i
    items=[]
    for k,i in best.items():
        r=rows[i]; age=(T-datetime.date.fromisoformat(r['date'])).days
        w=math.sqrt(r['n']/1000)*0.5**(age/21)*(0.5 if r['key']=='oru' else 1)
        items.append((i,w))
    return items
def mix(items,f):
    S=sum(w for _,w in items); return sum(w*f(MO[i]) for i,w in items)/S
NOW=datetime.date.fromisoformat(os.environ['VV_TODAY']) if os.environ.get('VV_TODAY') else datetime.date.today()
pts=[NOW-datetime.timedelta(days=k) for k in range(0,170)][::-1]
pts=[p for p in pts if len(pick(p))>=3]
ser={'dates':[p.isoformat() for p in pts]}
for c in ['ALP','LNP','GRN','ONP']: ser[c]=[]
ser['pL']=[]; ser['n']=[]
seatSer={n:{c:[] for c in ['ALP','LNP','GRN','ONP']} for n in MO[0]['seats']}
for p in pts:
    it=pick(p)
    for c in ['ALP','LNP','GRN','ONP']: ser[c].append(round(mix(it,lambda m:m['summary']['exp'][c]),1))
    ser['pL'].append(round(mix(it,lambda m:m['summary']['pLNPmaj'])*100))
    ser['n'].append(len(it))
    for n in seatSer:
        for c in ['ALP','LNP','GRN','ONP']:
            seatSer[n][c].append(round(mix(it,lambda m:m['seats'][n]['prob'][c])))
print(ser['dates'][0],ser['dates'][-1],len(pts))
for c in ['ALP','LNP','GRN','ONP']: print(c,ser[c])
print('pL',ser['pL'])
# 2) current blend
D=json.load(open('app-data.json'))
it=pick(NOW); S=sum(w for _,w in it)
it.sort(key=lambda x:-x[1])
D['summary']={'exp':{c:mix(it,lambda m,c=c:m['summary']['exp'][c]) for c in codes},'pLNPmaj':mix(it,lambda m:m['summary']['pLNPmaj']),'pALPmaj':mix(it,lambda m:m['summary']['pALPmaj']),'pHung':mix(it,lambda m:m['summary']['pHung']),'pLNPONPmaj':mix(it,lambda m:m['summary']['pLNPONPmaj'])}
D['ranges']={c:[round(mix(it,lambda m,c=c:m['ranges'][c][0])),round(mix(it,lambda m,c=c:m['ranges'][c][1]))] for c in codes}
avg={}
for c,k in (('ALP','alp'),('LNP','lnp'),('GRN','grn'),('ONP','onp')): avg[c]=sum(w*rows[i][k] for i,w in it)/S
avg['OTH']=100-sum(avg.values()); D['avg']=avg
for n,s in D['seats'].items():
    prob={c:round(mix(it,lambda m,c=c:m['seats'][n]['prob'][c]),1) for c in codes}
    proj={c:round(mix(it,lambda m,c=c:m['seats'][n]['proj'][c]),1) for c in codes}
    fav=max(prob,key=prob.get); s['prob']=prob; s['proj']=proj; s['fav']=fav; s['favP']=prob[fav]
    pairs={}
    for i,w in it:
        k='-'.join(MO[i]['seats'][n]['finalTwo']); pairs[k]=pairs.get(k,0)+w
    s['finalTwo']=max(pairs,key=pairs.get).split('-'); s.pop('finalTwoP',None)
    s['byPoll']=[{c:round(MO[i]['seats'][n]['prob'][c]) for c in ['ALP','LNP','GRN','ONP','IND']} for i,w in it]
tr=[]
for j,(i,w) in enumerate(it):
    r=rows[i]; nm,sh=NAME[r['key']]
    tr.append({'name':nm,'short':sh,'date':r['label'].replace('Sept','Sep').replace('July','Jul').replace('June','Jun'),'n':r['n'],'w':round(w/S*100,1),'ALP':r['alp'],'LNP':r['lnp'],'GRN':r['grn'],'ONP':r['onp'],'comm':r['key']=='oru','idx':j,'iso':r['date'],
      'exp':{c:round(MO[i]['summary']['exp'][c]) for c in ['ALP','LNP','GRN','ONP']},'pL':round(MO[i]['summary']['pLNPmaj']*100)})
D['trust']=tr; D['series']=ser; D['seatSeries']=seatSer
D.pop('polls',None); D.pop('pollShorts',None)
json.dump(D,open('app-data.json','w'),separators=(',',':'))
print({c:round(v,1) for c,v in D['summary']['exp'].items()},round(D['summary']['pLNPmaj']*100),round(D['summary']['pHung']*100))
for t in tr: print(t['short'],t['date'],t['w'],t['exp'],t['pL'])
print(os.path.getsize('app-data.json'))
