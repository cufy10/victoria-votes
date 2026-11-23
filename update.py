#!/usr/bin/env python3
"""Daily refresh for the Victoria Votes 2026 website.

What it does, in order:
  1. Fetches the latest polls, election page and candidate page from Wikipedia.
  2. Parses every dated 2026 statewide poll.
  3. Collects the latest dated news headlines cited on those pages.
  4. Runs the seat model, builds the daily seat history, blends the polls by trust.
  5. Builds out/index.html (the website file).

Exit codes: 0 = built OK, 2 = a check failed (nothing written), 3 = could not fetch polls.
Run it with:  python3 update.py
"""
import os, sys, re, json, datetime, subprocess, urllib.request, urllib.parse, concurrent.futures

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, 'data')
OUT = os.path.join(ROOT, 'out')
UA = 'election-map-updater/1.0'
PAGES = {
    'polls.txt': 'Opinion_polling_for_the_2026_Victorian_state_election',
    'main.txt': '2026_Victorian_state_election',
    'cands.txt': 'Candidates_of_the_2026_Victorian_state_election',
}
try:
    import zoneinfo
    TODAY = datetime.datetime.now(zoneinfo.ZoneInfo('Australia/Melbourne')).date()
except Exception:
    TODAY = datetime.date.today()


def log(*a):
    print('[update]', *a, flush=True)


def fail(code, msg):
    log('FAILED:', msg)
    sys.exit(code)


# ---------------------------------------------------------------- 1. fetch
def fetch(title):
    url = ('https://en.wikipedia.org/w/api.php?action=parse&page=' + urllib.parse.quote(title)
           + '&prop=wikitext&format=json&formatversion=2')
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)['parse']['wikitext']


for fname, title in PAGES.items():
    try:
        txt = fetch(title)
        if len(txt) < 20000:
            raise ValueError('page looks too short')
        open(os.path.join(DATA, fname), 'w').write(txt)
        log('fetched', fname, len(txt))
    except Exception as e:
        if fname == 'polls.txt':
            fail(3, 'could not fetch polls: %s' % e)
        log('warning: could not fetch %s (%s); using the saved copy' % (fname, e))

# ---------------------------------------------------------------- 2. polls
MON = {m: i + 1 for i, m in enumerate(['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'])}
FIRM = {'Lighthouse': 'lighthouse', 'RedBridge': 'redbridge', 'Resolve': 'resolve', 'DemosAU': 'demos',
        'Roy Morgan': 'morgan', 'Newspoll': 'newspoll', 'Online Research': 'oru', 'Freshwater': 'freshwater',
        'YouGov': 'yougov'}


def end_date(s):
    s = s.replace('–', '-').replace('—', '-')
    last = s.split('-')[-1].strip()
    m = re.match(r'^(\d{1,2})\s*([A-Za-z]+)$', last) or re.search(r'(\d{1,2})\s*([A-Za-z]+)\s*$', s)
    if not m:
        return None
    mon = MON.get(m.group(2)[:3].lower())
    return datetime.date(TODAY.year, mon, int(m.group(1))) if mon else None


def parse_polls(txt):
    i = txt.index('====2026====')
    j = txt.index('====2025====')
    sec = txt[i:j]
    rows = []
    for p in re.split(r'\n\|-(?: [^\n]*)?\n', sec):
        if not re.match(r'\s*\|\s*(?:rowspan="\d+"\s*\|\s*|style=[^|]*\|\s*)?(?:\{\{nowrap\|)?[\d –\-A-Za-z]+', p):
            continue
        q = re.sub(r'<ref[^>]*/>', '', p)
        q = re.sub(r'<ref[^>]*>.*?</ref>', '', q, flags=re.S)
        q = re.sub(r'\{\{[^}]*\}\}', '', q)
        q = re.sub(r'\[https?://[^\]]*\]', '', q)
        q = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]*)\]\]', r'\1', q)
        lines = [l for l in q.split('\n') if l.strip()]
        if len(lines) < 6:
            continue

        def cell(l):
            l = l.strip().lstrip('|!').strip()
            l = re.sub(r'^(?:rowspan="?\d+"?\s*\|?|style="[^"]*"\s*\|?|style=[^|\s]*\s*\||colspan=\d+\s*\||align=\S+\s*\|)+', '', l).strip()
            return l.replace("'''", '').strip(' ;|')
        cells = [cell(l) for l in lines]
        date, firm = cells[0], cells[1]
        pcts = []
        for c in cells[2:]:
            for x in re.findall(r'(\d+(?:\.\d+)?)\s*%', c):
                pcts.append(float(x))
        if len(pcts) < 4 or not re.search(r'[A-Za-z]', firm):
            continue
        d = end_date(date)
        key = next((v for k, v in FIRM.items() if k in firm), None)
        if not d or not key:
            log('skipping poll row:', date, '|', firm[:30])
            continue
        n = cells[3] if len(cells) > 3 else ''
        n = int(n.replace(',', '')) if re.match(r'^[\d,]+$', n or '') else 1000
        rows.append({'date': d.isoformat(), 'key': key, 'firm': firm, 'n': n, 'alp': pcts[0], 'lnp': pcts[1],
                     'grn': pcts[2], 'onp': pcts[3], 'label': date})
    rows.sort(key=lambda r: r['date'], reverse=True)
    return rows


rows = parse_polls(open(os.path.join(DATA, 'polls.txt')).read())
log('parsed', len(rows), 'polls; newest', rows[0]['date'] if rows else None)
if len(rows) < 20:
    fail(2, 'only %d polls parsed (expected 25+); the Wikipedia table format may have changed' % len(rows))
if (TODAY - datetime.date.fromisoformat(rows[0]['date'])).days > 30:
    fail(2, 'newest poll is more than 30 days old')
json.dump(rows, open(os.path.join(DATA, 'rows_clean.json'), 'w'))

# ---------------------------------------------------------------- 3. news
def pdate(s):
    s = s.strip()
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', s)
    if m:
        return datetime.date(int(m[1]), int(m[2]), int(m[3]))
    m = re.match(r'(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})', s)
    if m and m[2][:3].lower() in MON:
        return datetime.date(int(m[3]), MON[m[2][:3].lower()], int(m[1]))
    m = re.match(r'([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})', s)
    if m and m[1][:3].lower() in MON:
        return datetime.date(int(m[3]), MON[m[1][:3].lower()], int(m[2]))
    return None


txt = '\n'.join(open(os.path.join(DATA, f)).read() for f in ('cands.txt', 'main.txt', 'polls.txt'))
NEWS_HOSTS = (r'abc\.net\.au|theage\.com\.au|heraldsun\.com\.au|afr\.com|theaustralian\.com\.au|9news|sbs\.com\.au|theguardian|'
              r'smh\.com\.au|news\.com\.au|skynews|canberratimes|crikey|theconversation|7news|bendigoadvertiser|starcommunity|'
              r'timesnewsgroup|castlemainemail|latrobevalleyexpress|sheppnews|sgst')
items = {}
for blk in re.findall(r'\{\{\s*[Cc]ite (?:web|news)[^{}]*\}\}', txt, flags=re.S):
    f = {}
    for k, v in re.findall(r'\|\s*([\w-]+)\s*=\s*([^|}]*)', blk):
        f[k.strip().lower()] = v.strip()
    d = pdate(f.get('date', '') or f.get('access-date', ''))
    if not d or d < TODAY - datetime.timedelta(days=60) or d > TODAY:
        continue
    url, title = f.get('url', ''), f.get('title', '')
    if not url.startswith('http') or not title or not re.search(NEWS_HOSTS, url):
        continue
    pub = f.get('website') or f.get('work') or f.get('newspaper') or f.get('publisher') or re.sub(r'^https?://(www\.)?([^/]+).*', r'\2', url)
    title = re.sub(u"[\u2018\u2019]", "'", title).strip()
    if title.startswith("'") and title.count("'") % 2 == 1:
        title = title[1:]
    items[url] = (d, pub, title, url)
news = sorted(items.values(), reverse=True)

# Keep only stories that anyone can read for free (no subscription).
FREE_HOSTS = r'abc\.net\.au|theguardian\.com|theconversation\.com|sbs\.com\.au|9news\.com\.au|7news\.com\.au'
BROWSER_UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15',
              'Accept': 'text/html'}


def is_free(item):
    url = item[3]
    if not re.search(FREE_HOSTS, url):
        return False
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=BROWSER_UA), timeout=20)
        if r.status != 200:
            return False
        body = r.read(900000).decode('utf-8', 'ignore')
        return not re.search(r'"isAccessibleForFree"\s*:\s*"?false"?', body, re.I)
    except Exception:
        return False


with concurrent.futures.ThreadPoolExecutor(6) as ex:
    free_flags = list(ex.map(is_free, news))
log('news: %d candidates, %d free to read' % (len(news), sum(free_flags)))
news = [n for n, ok in zip(news, free_flags) if ok]
json.dump([[d.isoformat(), p, t, u] for d, p, t, u in news], open(os.path.join(DATA, 'news_cands.json'), 'w'))
log('news candidates:', len(news))

# ---------------------------------------------------------------- 4. model
def run(script, *args):
    env = dict(os.environ, VV_TODAY=TODAY.isoformat())
    r = subprocess.run([sys.executable, '-I', script] + list(args), cwd=DATA, capture_output=True, text=True, env=env)
    if r.returncode != 0:
        log(r.stdout[-1500:], r.stderr[-1500:])
        fail(2, '%s failed' % script)
    return r.stdout


run('model.py')       # base model -> model_out.json
run('assemble.py')    # seat records -> app-data.json
log('running the seat model for every poll (about a minute)...')
out = run('timeseries.py')   # per-poll runs, daily history, trust-weighted blend
run('photos.py')      # free-licensed photos for people in the news (cached)
run('post.py')        # news, notes, dates

# ---------------------------------------------------------------- 5. build + checks
D = json.load(open(os.path.join(DATA, 'app-data.json')))
exp = D['summary']['exp']
total = sum(exp[k] for k in ('ALP', 'LNP', 'GRN', 'ONP', 'IND', 'OTH'))
checks = [
    (len(D['seats']) == 88, 'expected 88 seats'),
    (84 <= total <= 88.6, 'expected seats should total about 88, got %.1f' % total),
    (len(D['trust']) >= 4, 'fewer than 4 pollsters in the blend'),
    (len(D['series']['dates']) >= 30, 'history has fewer than 30 days'),
    (all(abs(sum(s['prob'].values()) - 100) < 2 for s in D['seats'].values()), 'a seat win-chance does not add to 100'),
    (not re.search(r'[:\[,]\s*(-?Infinity|NaN)\b', json.dumps({k: v for k, v in D.items() if k != 'photos'})), 'NaN found in data'),
]
for ok, msg in checks:
    if not ok:
        fail(2, msg)

tpl = open(os.path.join(ROOT, 'template.html')).read()
data = json.dumps(D, separators=(',', ':')).replace('</', '<\\/')
html = (tpl.replace('__DATA__', data).replace('__UPDATED__', D['meta']['updated'])
        .replace('__NPOLLS__', str(len(D['trust']))).replace('__POLLRANGE__', D['meta']['pollRange']))
if any(p in html for p in ('__DATA__', '__UPDATED__', '__NPOLLS__', '__POLLRANGE__')):
    fail(2, 'template placeholders were not filled')
if not (500_000 < len(html) < 4_000_000):
    fail(2, 'output size looks wrong: %d bytes' % len(html))
os.makedirs(OUT, exist_ok=True)
open(os.path.join(OUT, 'index.html'), 'w').write(html)

# ---- public web page (GitHub Pages): full HTML document with a proper head and link-preview tags
SITE = os.path.join(ROOT, 'site')
os.makedirs(SITE, exist_ok=True)
body = re.sub(r'<title>.*?</title>\s*', '', html, count=1, flags=re.S)
body = re.sub(r'<meta name="claude:viewport-fit-sides"[^>]*>\s*', '', body, count=1)
desc = ('An independent, unofficial guide to the Victorian state election on Saturday 28 November 2026: '
        'find your seat, see who is running and read a model estimate of who is likely to win.')
head = ('<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<title>Victoria Votes 2026</title>'
        '<meta name="description" content="%s">'
        '<meta property="og:type" content="website"><meta property="og:site_name" content="Victoria Votes 2026">'
        '<meta property="og:title" content="Victoria Votes 2026: find your seat">'
        '<meta property="og:description" content="%s">'
        '<meta property="og:url" content="https://victoriavotes.github.io/"><meta property="og:image" content="https://victoriavotes.github.io/og.jpg"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Map of Victoria with the words Find your seat. See who is likely to win it.">'
        '<link rel="canonical" href="https://victoriavotes.github.io/">'
        '<meta name="twitter:card" content="summary_large_image"><meta name="twitter:image" content="https://victoriavotes.github.io/og.jpg"><meta name="twitter:title" content="Victoria Votes 2026: find your seat">'
        '<meta name="twitter:description" content="%s">'
        '<meta name="theme-color" content="#0F1B3D">'
        '<style>:root{color-scheme:light;box-sizing:border-box;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'html{scroll-padding-top:env(safe-area-inset-top,0px)}body{margin:0;padding:0;font:14px -apple-system,BlinkMacSystemFont,sans-serif;background:#fff;color:#000}'
        'img{max-width:100%%}[hidden]:not([hidden=until-found i]){display:none!important}</style></head><body>') % (desc, desc, desc)
open(os.path.join(SITE, 'index.html'), 'w').write(head + body + '</body></html>')
open(os.path.join(SITE, '.nojekyll'), 'w').write('')
_og = os.path.join(ROOT, 'og.b64')
if os.path.exists(_og):  # share-preview picture, stored as text in the repo
    import base64
    open(os.path.join(SITE, 'og.jpg'), 'wb').write(base64.b64decode(open(_og).read().strip()))
summary = {
    'built': TODAY.isoformat(), 'updated_label': D['meta']['updated'], 'polls_used': len(D['trust']),
    'newest_poll': rows[0]['date'], 'poll_range': D['meta']['pollRange'],
    'seats': {k: round(exp[k]) for k in ('LNP', 'ALP', 'ONP', 'GRN')},
    'coalition_majority_pct': round(D['summary']['pLNPmaj'] * 100),
    'history_days': len(D['series']['dates']), 'news_items': len(D['news']), 'bytes': len(html),
}
json.dump(summary, open(os.path.join(OUT, 'last_run.json'), 'w'), indent=1)
log('OK', json.dumps(summary))
