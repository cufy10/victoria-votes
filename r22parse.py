import re, json
d=open('r22.txt').read()
heads=[(m.start(),m.group(1)) for m in re.finditer(r'^===([^=]+)===$',d,re.M)]
res={}
def grp(party):
    p=party.lower()
    if 'labor' in p: return 'ALP'
    if 'liberal' in p and 'democrat' not in p: return 'LNP'
    if 'national' in p: return 'LNP'
    if 'green' in p: return 'GRN'
    if p.startswith('independent') or p.startswith('ind.') or p.startswith('ind '): return 'IND'
    return 'OTH'
for i,(pos,name) in enumerate(heads):
    end=heads[i+1][0] if i+1<len(heads) else len(d)
    blk=d[pos:end]
    prim=blk.split('Election box formal')[0]
    shares={'ALP':0,'LNP':0,'GRN':0,'IND':0,'OTH':0}
    top_ind=0
    for b in prim.split('{{Election box candidate')[1:]:
        pm=re.search(r'\|\s*party\s*=\s*([^\n]*)',b); qm=re.search(r'\|\s*percentage\s*=\s*([\d.]+)',b)
        if not pm or not qm: continue
        g=grp(pm.group(1)); pct=float(qm.group(1)); shares[g]+=pct
        if g=='IND': top_ind=max(top_ind,pct)
    # 2PP ALP v LIB (first 2pp section)
    pp=None
    m=re.search(r'Election box (?:2pp|n2pp)\}\}(.*?)(?:Election box 2cp|Election box hold)',blk,re.S)
    if m:
        for mm in re.finditer(r'\|(?:candidate = .*?\n\|)?party = (.*?)\n(?:\|candidate = .*?\n)?\|votes = [^\n]*\n\|percentage = ([\d.]+)',m.group(1)):
            if 'labor' in mm.group(1).lower(): pp=float(mm.group(2))
    res[name.strip()]={'p':shares,'topInd':top_ind,'alp2pp':pp}
json.dump(res,open('r22_parsed.json','w'),indent=0)
print(len(res))
for k in ['Albert Park','Mornington','Melbourne','Hawthorn','Morwell']: print(k,res[k])
tot={g:sum(v['p'][g] for v in res.values())/88 for g in ['ALP','LNP','GRN','IND','OTH']}
print(tot, sum(tot.values()))
