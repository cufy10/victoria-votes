import json,re
D=json.load(open('app-data.json'))
for s in D['seats'].values():
    for o in s['others']:
        if o['party']=='Nat': o['party']='Nationals'
N=json.load(open('news_cands.json')); out=[]
for d,p,t,u in N:
    if '/guide/' in u or 'liberals-to-preference-one-nation' in u: continue
    p=re.sub(r'\[\[|\]\]','',p)
    pl=p.lower()
    p='The Guardian' if 'guardian' in pl else 'ABC News' if (pl.startswith('abc') or 'broadcasting' in pl) else 'The Conversation' if 'conversation' in pl else 'SBS News' if 'sbs' in pl else p
    tl=t.lower()
    tag='Polls' if re.search(r'poll|lead|tracking|preferred premier|wipeout|rump',tl) else 'Candidates' if re.search(r'candidate|disendorse|dump|stands down|apologise|legal letter|mp attendance|cheeseman',tl) else 'Campaign'
    out.append([d,p,t,u,tag])
D['news']=out[:18]
D['seats']['Williamstown']['notes']=['Paul Lindemann was disendorsed by the Liberals on 11 Nov 2026 but is still on the VEC candidate list for this seat.']
D['seats']['Bendigo West']['notes']=['Christos Harisopoulos was disendorsed by Family First on 18 Nov 2026 but is still on the VEC candidate list for this seat.']
for n in ('Ringwood','South Barwon'):
    D['seats'][n]['heldCode']='IND'; D['seats'][n]['held']='Independent (left Labor)'
import datetime
import os
today=datetime.date.fromisoformat(os.environ['VV_TODAY']) if os.environ.get('VV_TODAY') else datetime.date.today()
def _f(d): return str(d.day)+' '+d.strftime('%b')
isos=sorted(datetime.date.fromisoformat(x['iso']) for x in D['trust'])
D['meta']={'updated':str(today.day)+' '+today.strftime('%b %Y'),'pollRange':_f(isos[0])+'–'+_f(isos[-1])+' '+str(isos[-1].year)}
D['loc']=json.load(open('localities.json'))
import os
if os.path.exists('photos.json'): D['photos']=json.load(open('photos.json'))
SHORT={'lighthouse':'Lighthouse','redbridge':'RedBridge','resolve':'Resolve','demos':'DemosAU','morgan':'Roy Morgan','newspoll':'Newspoll','oru':'Online Research Unit','freshwater':'Freshwater','yougov':'YouGov'}
D['allPolls']=[[r['date'],r['key'],SHORT.get(r['key'],r['key']),r['label'].replace('Sept','Sep').replace('July','Jul').replace('June','Jun'),r['alp'],r['lnp'],r['grn'],r['onp']] for r in json.load(open('rows_clean.json'))]
D.pop('polls',None);D.pop('pollShorts',None)
json.dump(D,open('app-data.json','w'),separators=(',',':'))
print('post ok',len(D['news']))
