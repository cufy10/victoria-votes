import json, math, random
random.seed(2026)
R22=json.load(open('r22_parsed.json'))
CANDS={c['seat']:c for c in json.load(open('cands_parsed.json'))}
PEND={p[0]:p for p in json.load(open('pend.json'))}
GEO=json.load(open('districts.geojson'))

# ---- polls: five most recent statewide polls, 26 Oct - 13 Nov 2026
POLLS=[('Lighthouse / Growth Intelligence','13 Nov',21,32,14,23),
       ('RedBridge / Accent','3–10 Nov',23,31,15,22),
       ('Resolve Strategic','2–7 Nov',22,30,13,23),
       ('DemosAU / Premier National','30 Oct–5 Nov',18,33,17,21),
       ('Roy Morgan','26–29 Oct',22.5,29.5,12.5,22)]
AVG={k:sum(p[i] for p in POLLS)/len(POLLS) for k,i in [('ALP',2),('LNP',3),('GRN',4),('ONP',5)]}
AVG['OTH']=100-sum(AVG.values())
import os
if os.environ.get('POLL'):
    _p=json.loads(os.environ['POLL']); AVG={'ALP':_p[0],'LNP':_p[1],'GRN':_p[2],'ONP':_p[3]}; AVG['OTH']=100-sum(AVG.values())
print('poll avg',AVG)
S22={'ALP':37.0,'LNP':34.5,'GRN':11.5}

# ---- seat geography
def centroid(f):
    xs=[];ys=[];A=0;cx=0;cy=0
    for poly in f['geometry']['coordinates']:
        r=poly[0]
        for i in range(len(r)-1):
            x0,y0=r[i];x1,y1=r[i+1];a=x0*y1-x1*y0;A+=a;cx+=(x0+x1)*a;cy+=(y0+y1)*a
    return (cx/(3*A),cy/(3*A)) if A else (0,0)
def km(lon,lat):
    return math.hypot((lon-144.9631)*math.cos(math.radians(37.8))*111.2,(lat+37.8136)*111.2)
PROV={'Geelong','Bellarine','South Barwon','Lara','Wendouree','Eureka','Bendigo East','Bendigo West','Mildura','Shepparton','Morwell'}
LOW_ONP={'Dandenong','Clarinda','Oakleigh','Box Hill','Glen Waverley','Broadmeadows','Thomastown','Laverton','Mulgrave','Narre Warren North','Mill Park','Bundoora','Tarneit','Point Cook'}
info={}
for f in GEO['features']:
    n=f['properties']['name']; reg=f['properties']['region']
    lon,lat=centroid(f); d=km(lon,lat)
    if 'Metropolitan' in reg:
        cls='Inner Melbourne' if d<9 else ('Middle Melbourne' if d<23 else 'Outer Melbourne')
        w={'Inner Melbourne':0.5,'Middle Melbourne':0.85,'Outer Melbourne':1.2}[cls]
    elif n in PROV: cls,w='Regional city',1.0
    elif d<45 and n not in ('Macedon',): cls,w='Outer Melbourne',1.2
    else: cls,w='Rural and regional',1.3
    if n in LOW_ONP: w*=0.75
    info[n]={'cls':cls,'w':w,'cx':round(lon,4),'cy':round(lat,4),'region':reg}
# manual region fixes for Eastern Vic seats on the metro fringe
for n in ('Pakenham','Cranbourne','Berwick','Hastings','Nepean','Bass','Evelyn','Monbulk'):
    if info[n]['cls']in('Inner Melbourne','Middle Melbourne','Rural and regional'): pass
mw=sum(i['w'] for i in info.values())/88
for i in info.values(): i['w']/=mw
# Roy Morgan SMS poll (21-26 Oct, n=283): ONP ~39% in Hastings, Morwell, Pakenham
ONP_SEAT_POLL={'Hastings':39,'Morwell':39,'Pakenham':39}
SEAT_POLL={'Bass':{'a':'Liberal','b':'ALP','lead':'Liberal ahead','on':None},
           'Hastings':{'a':'One Nation','b':'Liberal','lead':'One Nation ahead','on':39},
           'Morwell':{'a':'One Nation','b':'ALP','lead':'One Nation ahead','on':39},
           'Pakenham':{'a':'One Nation','b':'ALP','lead':'One Nation ahead','on':39}}

PARTIES=['ALP','LNP','GRN','ONP','IND','OTH']
FLOW={'GRN':{'ALP':.74,'LNP':.08,'ONP':.04,'IND':.09,'OTH':.05},
      'OTH':{'ALP':.22,'LNP':.32,'ONP':.22,'GRN':.10,'IND':.14},
      'IND':{'ALP':.30,'LNP':.30,'ONP':.10,'GRN':.18,'OTH':.12},
      'ONP':{'LNP':.60,'ALP':.16,'GRN':.04,'IND':.12,'OTH':.08},
      'LNP':{'ONP':.48,'ALP':.22,'GRN':.08,'IND':.14,'OTH':.08},
      'ALP':{'GRN':.62,'IND':.14,'LNP':.10,'ONP':.08,'OTH':.06}}

CLSF={'ALP':{'Inner Melbourne':1.3,'Middle Melbourne':1.1,'Outer Melbourne':0.9,'Regional city':0.85,'Rural and regional':0.75},
      'GRN':{'Inner Melbourne':1.25,'Middle Melbourne':0.95,'Outer Melbourne':0.75,'Regional city':0.8,'Rural and regional':0.7},
      'LNP':{'Inner Melbourne':1.0,'Middle Melbourne':1.02,'Outer Melbourne':0.97,'Regional city':0.95,'Rural and regional':0.92}}
NORM={}
def _norm():
    for k in ('ALP','LNP','GRN'):
        tot=sum(R22[n]['p'][k]*CLSF[k][info[n]['cls']] for n in info)/88
        NORM[k]=AVG[k]/tot
_norm()
def base_shares(n, noise=None, shock=None):
    r=R22[n]['p']; c=CANDS[n]; inf=info[n]
    hasInd=any('(Ind)' in o for o in c['others'])
    ind=r['IND']; oth=r['OTH']
    if hasInd and R22[n]['topInd']>=8: indp=ind
    else: indp=0; oth+=ind
    cl=inf['cls']
    s={'ALP':r['ALP']*CLSF['ALP'][cl]*NORM['ALP'],
       'LNP':r['LNP']*CLSF['LNP'][cl]*NORM['LNP'],
       'GRN':r['GRN']*CLSF['GRN'][cl]*NORM['GRN'],
       'IND':indp*0.9,'OTH':oth*0.6}
    onp=AVG['ONP']*inf['w']
    if n in ONP_SEAT_POLL: onp=ONP_SEAT_POLL[n]
    s['ONP']=onp
    # personal vote for sitting members who are re-contesting
    for k,ck in (('ALP','ALP'),('LNP','COA')):
        if c['cands'][ck] and c['cands'][ck]['inc']: s[k]*=1.07
    # no candidate in a party -> zero
    if not c['cands']['GRN']: s['GRN']=0
    if not c['cands']['ONP']: s['ONP']=0
    return s

def simulate_seat(s, shock, noise_on=True):
    v={}
    for p in PARTIES:
        x=s[p]
        if noise_on and x>0:
            sd={'ONP':5.5,'IND':4.0}.get(p,4.2)
            x=max(0.3, x*(1+shock.get(p,0)) + random.gauss(0,sd)*math.sqrt(x/25))
        v[p]=x
    t=sum(v.values()); v={k:100*x/t for k,x in v.items()}
    alive=[p for p in PARTIES if v[p]>0]
    while len(alive)>2:
        lo=min(alive,key=lambda p:v[p]); alive.remove(lo)
        w={q:FLOW[lo].get(q,0)*(math.exp(random.gauss(0,.25)) if noise_on else 1) for q in alive}
        tw=sum(w.values()) or 1
        for q in alive: v[q]+=v[lo]*w[q]/tw
        v[lo]=0
    a,b=alive
    return (a if v[a]>=v[b] else b), tuple(sorted(alive,key=lambda p:-v[p])), v

N=int(os.environ.get('NSIM','3000'))
seats=sorted(info)
wins={n:{p:0 for p in PARTIES} for n in seats}
pairs={n:{} for n in seats}
tot_hist=[]; shares_acc={n:{p:[] for p in PARTIES} for n in seats}
base={n:base_shares(n) for n in seats}
for it in range(N):
    shock={'ALP':random.gauss(0,.11),'LNP':random.gauss(0,.08),'GRN':random.gauss(0,.12),'ONP':random.gauss(0,.15),'IND':random.gauss(0,.1),'OTH':random.gauss(0,.1)}
    tally={p:0 for p in PARTIES}
    for n in seats:
        w,pair,_=simulate_seat(base[n],shock)
        wins[n][w]+=1; tally[w]+=1
        pairs[n][pair]=pairs[n].get(pair,0)+1
    tot_hist.append(tally)
exp={p:sum(t[p] for t in tot_hist)/N for p in PARTIES}
print('expected seats',exp)
def P(f): return sum(1 for t in tot_hist if f(t))/N
summ={'exp':exp,
 'pALPmaj':P(lambda t:t['ALP']>=45),
 'pLNPmaj':P(lambda t:t['LNP']>=45),
 'pLNPONPmaj':P(lambda t:t['LNP']+t['ONP']>=45),
 'pALPGRNmaj':P(lambda t:t['ALP']+t['GRN']>=45),
 'pHung':P(lambda t:max(t['ALP'],t['LNP'])<45)}
print(summ)
import statistics
ranges={p:(sorted(t[p] for t in tot_hist)[int(N*.1)],sorted(t[p] for t in tot_hist)[int(N*.9)]) for p in PARTIES}
print(ranges)

# ---- assemble seat records
NAME={'ALP':'Labor','LNP':'Liberal/National','GRN':'Greens','ONP':'One Nation','IND':'Independent','OTH':'Other'}
out={}
for n in seats:
    c=CANDS[n]; pe=PEND[n]
    p=pe; prob={k:round(v/N*100,1) for k,v in wins[n].items()}
    top=max(prob,key=prob.get)
    topPair=max(pairs[n],key=pairs[n].get)
    pt=base[n]; tt=sum(pt.values())
    proj={k:round(100*v/tt,1) for k,v in pt.items()}
    r=R22[n]
    out[n]={'name':n,'region':info[n]['region'],'cls':info[n]['cls'],'cx':info[n]['cx'],'cy':info[n]['cy'],
      'held':{'ALP':'Labor','LIB':'Liberal','NAT':'Nationals','GRN':'Greens','IND':'Independent'}.get(pe[2],pe[2]),
      'heldCode':{'ALP':'ALP','LIB':'LNP','NAT':'LNP','GRN':'GRN'}.get(pe[2],'IND'),
      'member':pe[1],'margin':pe[3],
      'p22':{k:round(v,1) for k,v in r['p'].items()}, 'alp2pp22':r['alp2pp'],
      'cands':c['cands'],'others':c['others'],
      'prob':prob,'fav':top,'favP':prob[top],'proj':proj,
      'finalTwo':list(topPair),'finalTwoP':round(pairs[n][topPair]/N*100),
      'seatPoll':SEAT_POLL.get(n)}
json.dump({'seats':out,'summary':summ,'ranges':ranges,'avg':AVG,'polls':POLLS},open(os.environ.get('OUTF','model_out.json'),'w'))
# quick view
from collections import Counter
print(Counter(o['fav'] for o in out.values()))
for n in ['Northcote','Bass','Pakenham','Niddrie','Kew','Melbourne','Mornington','Hawthorn','Morwell','Brunswick','Gippsland East','Albert Park','Ripon']:
    o=out[n]; print(n,o['cls'],o['prob'],o['finalTwo'],o['proj'])
