"""Fetch free-licensed photos (Wikimedia Commons) of people who appear in news headlines.

Only photos with a free licence (CC BY, CC BY-SA, CC0, public domain) are kept, each with its credit line.
Result: data/photos.json  {key: {n: name, d: data-URI, c: credit, u: Commons page}}
Cached: people already in photos.json are not fetched again. Delete the file to refresh.
"""
import base64, html, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

UA = {'User-Agent': 'election-map-updater/1.0'}
PEOPLE = [  # key, Wikipedia page title
    ('carroll', 'Ben Carroll'),
    ('wilson', 'Jess Wilson'),
    ('cheeseman', 'Darren Cheeseman'),
    ('hanson', 'Pauline Hanson'),
    ('allan', 'Jacinta Allan'),
]
FREE = re.compile(r'^(CC BY(-SA)? \d|CC0|Public domain|PD)', re.I)


def get(url):
    for attempt in range(4):
        try:
            time.sleep(1.5)  # be polite to Wikimedia
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 3:
                raise
            time.sleep(10 * (attempt + 1))


def api(host, params):
    q = urllib.parse.urlencode(dict(params, format='json', formatversion=2))
    return json.loads(get('https://%s/w/api.php?%s' % (host, q)))


out = {}
if os.path.exists('photos.json'):
    out = json.load(open('photos.json'))

for key, title in PEOPLE:
    if key in out:
        continue
    try:
        pg = api('en.wikipedia.org', {'action': 'query', 'titles': title, 'prop': 'pageimages', 'piprop': 'name'})['query']['pages'][0]
        fname = pg.get('pageimage')
        if not fname:
            print('no image for', title)
            continue
        info = api('commons.wikimedia.org', {'action': 'query', 'titles': 'File:' + fname, 'prop': 'imageinfo',
                                             'iiprop': 'extmetadata|url|mime', 'iiurlwidth': 480})['query']['pages'][0]['imageinfo'][0]
        meta = info.get('extmetadata', {})
        lic = (meta.get('LicenseShortName', {}).get('value') or '').strip()
        if not FREE.match(lic) or 'nonfree' in json.dumps(meta.get('Restrictions', {})).lower():
            print('skipping %s: licence %r is not clearly free' % (title, lic))
            continue
        artist = html.unescape(re.sub(r'<[^>]+>', '', meta.get('Artist', {}).get('value') or '')).strip()
        artist = re.sub(r'\s+', ' ', artist)[:70] or 'Unknown'
        data = get(info['thumburl'])
        mime = info.get('mime', 'image/jpeg')
        out[key] = {
            'n': title,
            'd': 'data:%s;base64,%s' % (mime, base64.b64encode(data).decode()),
            'c': 'Photo: %s, %s, via Wikimedia Commons' % (artist, lic),
            'u': info.get('descriptionurl', ''),
        }
        print('ok', title, lic, len(data), 'bytes')
    except Exception as e:  # a missing photo must never stop the daily update
        print('could not get photo for', title, e)

json.dump(out, open('photos.json', 'w'), separators=(',', ':'))
print('photos:', list(out))
