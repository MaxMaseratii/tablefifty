"""Builds src/deals.js — the TableFifty deal database.
Sources checked 28 Sep 2026: First Table venue pages (title checked live), TheFork London deals pages 1-4 + Festival page,
Code Hospitality offers page, tastecard London page, chain offer pages via becleverwithyourcash.com (updated 28 Sep 2026),
delivery offers seen on HotUKDeals (Sep 2026), coffee/grocery loyalty schemes (workingfromcoffeeshops.co.uk, advocate-group.co.uk 17 Sep 2026).
"""
import json, re, glob, statistics, os, datetime
HERE = os.path.dirname(os.path.abspath(__file__))

SEEN = "2026-09-28"   # date the hand-added chain / TheFork / Code offers were last checked by hand
FT = "https://www.firsttable.co.uk/london/"
TF = "https://www.thefork.co.uk/restaurant/"

def slug(s): return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

def region_from_ft(path):
    seg = path.split('/')[0]
    return {'central': 'central', 'east': 'east', 'west': 'west', 'north': 'north', 'north-west-london': 'north',
            'south': 'south', 'south-west-london': 'south', 'south-east': 'south'}.get(seg, 'central')

def area_from_ft(path):
    parts = path.split('/')
    return parts[1].replace('-', ' ').title().replace("Kings Cross", "King's Cross") if len(parts) > 1 else ''

GEO = json.load(open(os.path.join(HERE, 'geo_cache.json')))
V = {}  # key -> venue
def venue(name, key=None, **kw):
    key = key or slug(name)
    v = V.get(key)
    if not v:
        v = {'id': key, 'n': name, 'a': '', 'reg': 'central', 'ct': 'london', 'c': 'generic', 'm': [], 's': 'smart', 'k': 'dine', 'o': []}
        V[key] = v
        for k, val in kw.items():
            if val or k == 'm': v[k] = list(val) if k == 'm' else val
        return v
    for k, val in kw.items():
        if k == 'm':
            for x in val:
                if x not in v['m']: v['m'].append(x)
        elif val and (not v.get(k) or v.get(k) in ('generic', '', 'smart')):
            v[k] = val
    return v

def offer(v, **o):
    o.setdefault('seen', SEEN)
    v['o'].append(o)

# ---------------- First Table (title verified live 28 Sep 2026) ----------------
# (name, path, cuisine, style, type)  type: d = first table of the night, l = lunch, b = breakfast, bl = breakfast & lunch
ft = [
 ("Korean Grill Kensington", "west/south-kensington/korean-grill-kensington", "korean", "smart", "d"),
 ("Asador Bar & Grill", "central/leicester-square/asador-bar-and-grill", "steak", "smart", "d"),
 ("Kapara Soho", "central/soho/kapara", "mezze", "smart", "d"),
 ("Kachori", "south/elephant-and-castle/kachori", "indian", "casual", "d"),
 ("Mare Street Market King's Cross", "central/kings-cross/mare-street-market-kings-cross", "pizza", "smart", "d"),
 ("Yamatora", "north-west-london/finchley-road/yamatora", "sushi", "smart", "d"),
 ("FARE Restaurant + Bar", "central/clerkenwell/fare", "italian", "smart", "d"),
 ("TOWN Restaurant", "central/covent-garden/town-restaurant", "british", "fancy", "d"),
 ("YORI BANJUM", "central/piccadilly/yori-banjum", "korean", "casual", "d"),
 ("Foley's", "central/fitzrovia/foleys", "thai", "smart", "d"),
 ("Miznon Soho", "central/soho/miznon-soho", "mezze", "casual", "d"),
 ("Oriole", "central/covent-garden/oriole-restaurant", "cocktails", "fancy", "d"),
 ("ZOYA Indian Lounge", "central/kings-cross/zoya-indian-lounge", "indian", "smart", "d"),
 ("Brother Marcus Covent Garden", "central/covent-garden/brother-marcus-covent-garden", "mezze", "casual", "d"),
 ("Le Bab Soho", "central/soho/le-bab-soho", "kebab", "casual", "d"),
 ("Le Bab Covent Garden", "central/covent-garden/le-bab-covent-garden", "kebab", "casual", "d"),
 ("Angelique's Wine House", "central/marylebone/angeliques-wine-house", "cocktails", "smart", "d"),
 ("Coq d'Argent", "east/bank/coq-dargent", "fine", "fancy", "d"),
 ("Fresh Feast", "east/spitalfields/fresh-feast", "generic", "casual", "d"),
 ("Amber", "east/aldgate/amber", "mezze", "smart", "d"),
 ("Arepa & Co Haggerston", "east/haggerston/arepa-and-co-haggerston-venezuelan-restaurant", "mexican", "casual", "d"),
 ("MATER1A", "west/notting-hill/mater1a", "generic", "smart", "d"),
 ("Six Portland Road", "west/holland-park/six-portland-road-2", "fine", "fancy", "d"),
 ("Erev", "west/notting-hill/erev-london", "generic", "smart", "d"),
 ("Sunday in Brooklyn Notting Hill", "west/notting-hill/sunday-in-brooklyn-notting-hill", "breakfast", "smart", "d"),
 ("The Resto", "north/islington/the-resto", "generic", "casual", "d"),
 ("Primos", "north/finsbury-park/primos", "generic", "casual", "d"),
 ("The Front Room", "north/finsbury-park/the-front-room", "breakfast", "casual", "bl"),
 ("Smith's Bar & Grill", "west/paddington/smiths-bar-and-grill", "breakfast", "smart", "b"),
 ("JW Steakhouse", "central/mayfair/jw-steakhouse", "steak", "fancy", "l"),
 ("Laguna", "west/ealing/laguna", "indian", "casual", "l"),
 ("STEREO Covent Garden", "central/covent-garden/stereo-covent-garden", "cocktails", "smart", "d"),
 ("Soho Wala", "central/soho/soho-wala", "indian", "casual", "d"),
 ("Souk", "central/covent-garden/souk", "mezze", "casual", "d"),
 ("Strongroom Pizza", "east/shoreditch/strongroom-bar", "pizza", "casual", "d"),
 ("The Edge Shoreditch", "east/shoreditch/the-edge-shoreditch", "generic", "casual", "d"),
 ("The Blues Kitchen Shoreditch", "east/shoreditch/the-blues-kitchen-shoreditch", "burger", "casual", "d"),
 ("Kricket Shoreditch", "east/shoreditch/kricket-shoreditch", "indian", "smart", "d"),
 ("Passione Vino Shoreditch", "east/shoreditch/passione-vino-shoreditch", "italian", "smart", "d"),
 ("Chakana London", "east/hackney/chakana-london", "mexican", "smart", "d"),
 ("The Blues Kitchen Brixton", "south-west-london/brixton/the-blues-kitchen-brixton", "burger", "casual", "d"),
 ("Bánh Bánh Brixton", "south-west-london/brixton/banh-banh-brixton", "vietnamese", "casual", "d"),
 ("Archway Battersea", "south-west-london/battersea/archway-battersea", "cocktails", "casual", "d"),
 ("Tonkotsu Clapham", "south-west-london/clapham/tonkotsu-clapham", "ramen", "casual", "d"),
 ("The Mitre Fulham", "west/fulham/the-mitre-fulham", "british", "casual", "d"),
 ("The Cumberland Arms", "west/hammersmith/the-cumberland-arms", "british", "casual", "d"),
 ("bonbon", "west/kensington/bonbon", "generic", "smart", "d"),
 ("Town House", "west/south-kensington/town-house", "british", "smart", "d"),
 ("La Bouffe", "west/fulham/la-bouffe", "fine", "smart", "d"),
 ("Patri Hammersmith", "west/hammersmith/patri-hammersmith", "indian", "casual", "d"),
 ("ULI Marylebone", "central/marylebone/uli-marylebone", "thai", "smart", "d"),
 ("Riding House Cafe Fitzrovia", "central/fitzrovia/riding-house-cafe-fitzrovia", "british", "smart", "d"),
 ("108 Brasserie", "central/marylebone/108-brasserie", "british", "smart", "d"),
 ("Caravan Fitzrovia", "central/fitzrovia/caravan-fitzrovia", "generic", "smart", "d"),
 ("Dinings", "central/marylebone/dinings", "sushi", "fancy", "d"),
 ("Casa Tua King's Cross", "central/kings-cross/casa-tua-kings-cross", "italian", "casual", "d"),
 ("Camino King's Cross", "central/kings-cross/camino-kings-cross", "tapas", "smart", "d"),
 ("Belushi's London Bridge", "central/london-bridge/belushis-london-bridge", "burger", "casual", "d"),
 ("Amazing Grace Canary Wharf", "east/canary-wharf/amazing-grace-canary-wharf", "cocktails", "smart", "d"),
 ("Franco Manca Canary Wharf", "east/canary-wharf/franco-manca-canary-wharf", "pizza", "casual", "d"),
 ("Hazev", "east/canary-wharf/hazev", "mezze", "smart", "d"),
 ("Bōkan 37", "east/isle-of-dogs/bokan-37", "fine", "fancy", "d"),
 ("Humble Grape Canary Wharf", "east/canary-wharf/humble-grape-canary-wharf", "cocktails", "smart", "d"),
 ("Brother Marcus Canary Wharf", "east/canary-wharf/brother-marcus-canary-wharf", "mezze", "casual", "d"),
 ("Sussex", "central/soho/sussex", "british", "fancy", "d"),
 ("Barshu", "central/soho/barshu", "chinese", "smart", "d"),
 ("Luso", "central/fitzrovia/luso", "tapas", "smart", "d"),
 ("Paro Indian", "central/covent-garden/paro-indian", "indian", "smart", "d"),
 ("The India Fleet Street", "central/fleet-street/the-india-fleet-street", "indian", "smart", "d"),
 ("Touro Wimbledon", "south-west-london/wimbledon/touro-wimbledon", "steak", "smart", "d"),
 ("TOKii", "central/marble-arch/tokii", "sushi", "fancy", "d"),
 ("Heliot Steak House", "central/soho/heliot-steak-house", "steak", "smart", "d"),
 ("Ensō", "east/brick-lane/enso", "generic", "smart", "d"),
]
FT_MEALS = {'d': ['d'], 'l': ['l'], 'b': ['b'], 'bl': ['b', 'l']}
MANUAL = {'london/' + path: (name, c, s, t) for name, path, c, s, t in ft}

# Full UK list: every restaurant page in First Table's public sitemap, each page checked once (see ft_crawl.py).
PAGES = {}
for fn in glob.glob(os.path.join(HERE, 'ft_pages*.jsonl')):
    for line in open(fn):
        r = json.loads(line); PAGES[r['path']] = r
CZ_PRIORITY = [
 ('caribbean', {'Caribbean', 'Jamaican'}), ('pizza', {'Pizza'}), ('ramen', {'Ramen'}), ('sushi', {'Japanese', 'Sushi'}),
 ('korean', {'Korean'}), ('vietnamese', {'Vietnamese'}), ('thai', {'Thai'}), ('chinese', {'Chinese', 'Cantonese', 'Hong Kong', 'Hotpot'}),
 ('indian', {'Indian', 'South Indian', 'Nepalese', 'Sri Lankan', 'Bangladesh', 'Bengali', 'Pakistani', 'Indo-Chinese'}),
 ('mexican', {'Mexican', 'Latin American', 'Peruvian', 'South American'}), ('steak', {'Steakhouse', 'Grill & barbeque', 'Argentinian', 'Brazilian'}),
 ('burger', {'Burgers', 'American', 'Canadian', 'Fast food'}), ('tapas', {'Spanish', 'Portuguese'}),
 ('mezze', {'Greek', 'Turkish', 'Middle Eastern', 'Persian', 'Lebanese', 'Syrian', 'Mediterranean', 'Moroccan', 'North African', 'Afghanistan'}),
 ('italian', {'Italian', 'Sicilian'}), ('breakfast', {'Brunch', 'Breakfast', 'Cafe'}),
 ('fine', {'French', 'Fine dining', 'European', 'Scandinavian', 'German', 'Brasserie'}), ('british', {'British', 'Pub Food', 'Scottish', 'Irish', 'Seafood'}),
 ('tapas', {'Small plates'}), ('thai', {'Asian', 'Modern Asian', 'Filipino', 'Indonesian', 'Malaysian', 'Fusion'})]
def ft_cuisine(tags):
    cz = {t for cat, t in tags if cat == 'Cuisine'}
    for key, names in CZ_PRIORITY:
        if cz & names: return key
    return 'generic'
def ft_style(rec):
    price = [t for cat, t in rec.get('tags', []) if cat == 'Price']
    if price:
        n = len(price[0].strip())
        return 'casual' if n <= 2 else 'smart' if n == 3 else 'fancy'
    m = re.findall(r'\d+', rec.get('mains') or '')
    top = int(m[-1]) if m else 25
    return 'casual' if top <= 25 else 'smart' if top <= 45 else 'fancy'
def ft_type(meta):
    m = meta.lower()
    if 'first table of the night' in m: return 'd'
    if 'breakfast and lunch' in m: return 'bl'
    if 'breakfast' in m: return 'b'
    if 'lunch' in m: return 'l'
    return None
CITY_NAMES = {}
CITY_PTS = {}
ft_live = 0
for path, rec in sorted(PAGES.items()):
    if rec.get('err') or rec.get('status') != 'Live' or not rec.get('ft') or rec.get('show') is False: continue
    typ = ft_type(rec.get('meta') or '')
    if not typ: continue          # e.g. "Book any time at everyday prices" = no discount
    city = path.split('/')[0]
    CITY_NAMES[city] = rec.get('region') or city.replace('-', ' ').title()
    name = re.sub(r'\s+-\s+' + re.escape(rec.get('city') or '#') + r'$', '', (rec.get('title') or '').strip())
    man = MANUAL.get(path)
    if man: name = man[0]
    try: ll = [round(float(rec['lat']), 4), round(float(rec['lng']), 4)]
    except (TypeError, ValueError, KeyError): ll = None
    if ll and not (49.8 < ll[0] < 61 and -8.8 < ll[1] < 2.1): ll = None
    if ll: CITY_PTS.setdefault(city, []).append(ll)
    sub = (rec.get('suburb') or '').strip()
    cityname = CITY_NAMES[city]
    area = sub if cityname.lower() in sub.lower() else (f"{sub}, {cityname}" if sub else cityname)
    meals = []
    for sess in rec.get('sessions') or []:
        k = {'breakfast': 'b', 'lunch': 'l', 'dinner': 'd', 'dinner2': 'd'}.get(sess)
        if k and k not in meals: meals.append(k)
    if not meals: meals = FT_MEALS[typ]
    c = man[1] if man else ft_cuisine(rec.get('tags', []))
    st = man[2] if man else ft_style(rec)
    if city == 'london':
        key = slug(name)
        reg = region_from_ft(path[len('london/'):])
    else:
        key = slug(name + '-' + city); reg = city
    v = venue(name, key=key, a=area, reg=reg, ct=city, c=c, s=st, m=meals)
    if ll: v['ll'] = ll
    v.setdefault('_tags', set()).update(t for cat, t in rec.get('tags', []) if cat != 'Cuisine')
    ig = (rec.get('instagram') or '').strip()
    if re.match(r'^https?://(www\.)?instagram\.com/[A-Za-z0-9_.]+/?', ig) and 'ig' not in v: v['ig'] = ig.split('?')[0]
    web = (rec.get('website') or '').strip()
    if re.match(r'^https?://', web) and 'instagram.com' not in web and 'web' not in v: v['web'] = web
    if rec.get('menus') and 'menu' not in v: v['menu'] = 'https://images.firsttable.net/' + rec['menus'][0].lstrip('/')
    o = dict(p='firsttable', u='https://www.firsttable.co.uk/' + path, h='ft_' + typ, n=50, live=True, seen=rec.get('checked') or SEEN)
    rt, cnt = rec.get('rating') or 0, rec.get('reviews') or 0
    if rt and cnt >= 10: o['r'] = [round(rt * 2, 1), cnt, 'ft']
    offer(v, **o)
    ft_live += 1
# hand-checked London pages that the sitemap check did not cover
for path, (name, c, s, t) in MANUAL.items():
    if path in PAGES: continue
    v = venue(name, a=area_from_ft(path[len('london/'):]) + ", London", reg=region_from_ft(path[len('london/'):]), c=c, s=s, m=FT_MEALS[t])
    offer(v, p='firsttable', u=FT + path[len('london/'):], h='ft_' + t, n=50, live=True)
    ft_live += 1
print('First Table offers:', ft_live)

# ---------------- TheFork (deals pages 1-4 + Festival, 28 Sep 2026) ----------------
# (name, area, region, cuisine, avg £, rating, reviews, max discount %, url slug)
tf = [
 ("Hans' Bar and Grill", "Chelsea", "west", "british", 30, 9.4, 595, 30, "hans-bar-and-grill-r815695"),
 ("Amor Gastronomia", "Holloway", "north", "italian", 25, 9.4, 958, 30, "amor-gastronomia-r811617"),
 ("Cuore Di Napoli", "North West London", "north", "pizza", 25, 9.3, 34, 50, "cuore-di-napoli-r865885"),
 ("The India Monument", "City of London", "central", "indian", 22, 9.0, 1424, 50, "the-india-monument-r808596"),
 ("Bustronome London", "South Bank", "south", "fine", 70, 9.5, 102, 30, "bustronome-london-r715820"),
 ("Spice Trader", "City of London", "central", "indian", 32, 9.5, 25, 50, "spice-trader-r865571"),
 ("Yatri at West Kensington", "West Kensington", "west", "indian", 25, 9.2, 507, 30, "yatri-at-west-kensington-r828992"),
 ("Parlay Mayfair", "Mayfair", "central", "thai", 46, 9.2, 18, 50, "parlay-mayfair-r850979"),
 ("Bengal Village", "Brick Lane", "east", "indian", 20, 8.9, 247, 50, "bengal-village-best-of-brick-lane-r840085"),
 ("Sushi Circle Fulham", "Fulham", "west", "sushi", 20, 9.5, 95, 20, "sushi-circle-fulham-r835000"),
 ("The India City Road", "Islington", "north", "indian", 25, 8.7, 1236, 20, "the-india-city-road-r814003"),
 ("The Famous Curry Bazaar", "Brick Lane", "east", "indian", 20, 8.7, 109, 50, "the-famous-curry-bazaar-r744702"),
 ("Il Castelletto", "Bloomsbury", "central", "italian", 22, 8.8, 1396, 50, "il-castelletto-r747163"),
 ("The India Cannon Street", "City of London", "central", "indian", 22, 8.6, 280, 20, "the-india-cannon-street-r852307"),
 ("TOKii", "Marble Arch", "central", "sushi", 50, 9.0, 598, 30, "tokii-r839833"),
 ("The Chelsea Townhouse", "Chelsea", "west", "british", 30, 8.9, 85, 30, "the-chelsea-townhouse-r839956"),
 ("Amarcord Museum", "Bloomsbury", "central", "italian", 25, 8.6, 478, 50, "amarcord-museum-r833710"),
 ("Bellillo", "Fulham", "west", "italian", 25, 9.8, 2178, 50, "bellillo-r809230"),
 ("Sripur Restaurant", "City of London", "central", "indian", 20, 8.7, 657, 30, "sripur-restaurant-r825195"),
 ("Kendal Street Kitchen", "Paddington", "west", "mezze", 27, 9.6, 3516, 50, "kendal-street-kitchen-r830836"),
 ("Raos", "Dalston", "east", "thai", 29, 8.8, 182, 30, "raos-r842859"),
 ("The India Fleet Street", "Fleet Street", "central", "indian", 30, 8.5, 588, 20, "the-india-fleet-street-r842625"),
 ("The 71", "Walthamstow", "east", "generic", 30, 8.6, 48, 30, "the-71-r849973"),
 ("Standard Balti House", "Brick Lane", "east", "indian", 25, 8.2, 383, 50, "standard-balti-house-r736233"),
 ("Dell Boyz", "Tooting", "south", "burger", 20, 8.6, 826, 50, "dell-boyz-r818283"),
 ("Smoke & Pepper Dalston", "Dalston", "east", "burger", 25, 9.6, 19, 30, "smoke-pepper-dalston-r863433"),
 ("Zayna", "Marylebone", "central", "indian", 30, 9.3, 443, 20, "zayna-r747384"),
 ("DaLongYi Hot Pot", "Fitzrovia", "central", "chinese", 30, 8.2, 389, 50, "dalongyi-hot-pot-r844596"),
 ("Silk Road Flavours", "Fulham", "west", "mezze", 37, 9.7, 120, 50, "silk-road-flavours-r855026"),
 ("Chez Elles", "Brick Lane", "east", "fine", 37, 9.6, 379, 50, "chez-elles-r825704"),
 ("Escocesa", "Stoke Newington", "north", "tapas", 25, 9.6, 120, 50, "escocesa-r822847"),
 ("Schnitzel Heaven", "Hoxton", "east", "generic", 20, 9.5, 776, 50, "schnitzel-heaven-r806789"),
 ("Bar Esteban", "Crouch End", "north", "tapas", 27, 9.6, 339, 50, "bar-esteban-r802167"),
 ("Zzetta Soul Fired Pizza", "Canning Town", "east", "pizza", 20, 9.5, 866, 50, "zzetta-soul-fired-pizza-r724370"),
 ("The Bountiful Cow", "Holborn", "central", "steak", 30, 9.5, 616, 50, "the-bountiful-cow-r599145"),
 ("El Inca Plebeyo", "Islington", "north", "mexican", 30, 9.6, 627, 50, "el-inca-plebeyo-r597035"),
 ("Corretto By the Canal", "Camden", "north", "british", 22, 9.1, 1138, 50, "corretto-by-the-canal-r812305"),
 ("Amber Leaf London", "Hackney Road", "east", "thai", 30, 9.5, 197, 50, "amber-leaf-london-r857306"),
 ("Indian Room", "Balham", "south", "indian", 24, 9.4, 384, 50, "indian-room-r819744"),
 ("Il Pampero", "Belgravia", "central", "italian", 40, 9.4, 444, 50, "il-pampero-r807169"),
 ("Rabbit", "Chelsea", "west", "british", 30, 9.4, 385, 30, "rabbit-r735308"),
 ("Bombay Bicycle Chef", "Balham", "south", "indian", 25, 9.4, 784, 50, "bombay-bicycle-chef-r733068"),
 ("Platform 7 at Clermont Charing Cross", "Charing Cross", "central", "british", 30, 9.4, 1576, 50, "platform-7-at-clermont-charing-cross-r710583"),
 ("Rockwell Bistro & Wine Bar", "Trafalgar Square", "central", "mezze", 25, 9.4, 1127, 50, "rockwell-bistro-wine-bar-r693231"),
 ("The Midyeci", "Dalston", "east", "mezze", 29, 9.7, 155, 30, "the-midyeci-r840065"),
 ("Mate's Restaurant", "Clapham", "south", "mezze", 30, 9.4, 207, 40, "mate-s-restaurant-r831670"),
 ("Carluccio's Regent's Park", "Primrose Hill", "north", "italian", 25, 9.7, 484, 20, "carluccio-s-marriott-regents-park-r736208"),
 ("Masala Brick Lane", "Brick Lane", "east", "indian", 20, 9.2, 1067, 50, "masala-r676229"),
 ("Gazzab", "Shepherd's Bush", "west", "indian", 25, 9.5, 319, 30, "gazzab-r834819"),
 ("ANA Turkish Restaurant and Bar", "Earl's Court", "west", "mezze", 25, 9.4, 531, 30, "ana-turkish-restaurant-and-bar-r830134"),
 ("The Dandy Bar at The Mayfair Townhouse", "Mayfair", "central", "cocktails", 23, 8.9, 746, 50, "the-dandy-bar-at-the-mayfair-townhouse-r815706"),
 ("Mimo's Lounge", "Tooting", "south", "mezze", 15, 9.6, 100, 30, "mimo-s-lounge-bar-grill-r809296"),
 ("Figo Leyton", "Leyton", "east", "italian", 35, 9.5, 166, 30, "figo-leyton-r806273"),
 ("La Lluna", "Muswell Hill", "north", "tapas", 30, 9.3, 27, 20, "la-lluna-r840907"),
 ("Prosecco Caffè Soho", "Soho", "central", "italian", 25, 9.0, 2324, 50, "prosecco-caffe-soho-r829699"),
 ("Wandering Grapes", "Camden", "north", "italian", 25, 9.1, 227, 50, "wandering-grapes-r855218"),
 ("La Cucina di Ina", "Crystal Palace", "south", "italian", 24, 9.8, 88, 20, "la-cucina-di-ina-r806220"),
 ("Turmeric Kitchen Paddington", "Paddington", "west", "indian", 25, 9.5, 1962, 20, "turmeric-kitchen-paddington-r740044"),
 ("Schnitzel Heaven Victoria Park", "Victoria Park", "east", "generic", 32, 9.4, 106, 30, "schnitzel-heaven-victoria-park-r857145"),
 ("Itto Stoke Newington", "Stoke Newington", "north", "ramen", 30, 9.4, 114, 30, "itto-stoke-newington-branch-air-conditioned-r850974"),
 ("Baan Thai", "Eltham", "south", "thai", 21, 9.4, 95, 30, "baan-thai-r848674"),
 ("Koh-i-noor Palace", "Cricklewood", "north", "indian", 20, 9.5, 69, 30, "koh-i-noor-palace-r812395"),
 ("Antika Restaurant", "Maida Vale", "west", "mezze", 24, 9.3, 613, 20, "antika-restaurant-r804738"),
 ("The Sushi Co Lewisham", "Lewisham", "south", "sushi", 20, 9.3, 331, 30, "the-sushi-co-lewisham-r754354"),
 ("The Sushi Co Ealing Broadway", "Ealing", "west", "sushi", 17, 9.2, 975, 40, "the-sushi-co-ealing-broadway-r754337"),
 ("Gazette Brasserie Chancery", "Chancery Lane", "central", "fine", 30, 9.3, 1372, 30, "gazette-brasserie-chancery-r746224"),
 ("Bricco e Bacco", "Fitzrovia", "central", "italian", 50, 9.5, 89, 30, "bricco-e-bacco-r711662"),
 ("Bahara Indian Kitchen", "Brick Lane", "east", "indian", 30, 9.3, 103, 50, "bahara-indian-kitchen-culture-r851039"),
 ("Agrodolce London", "Fitzrovia", "central", "italian", 30, 9.2, 923, 20, "agrodolce-london-r835126"),
 ("Cheeky Chicos Clapham", "Clapham Junction", "south", "mexican", 22, 9.3, 532, 30, "cheeky-chicos-clapham-r833911"),
 ("Beasy", "Soho", "central", "burger", 18, 9.2, 421, 50, "beasy-r753279"),
 ("The Monsoon", "Brick Lane", "east", "indian", 17, 9.2, 330, 50, "the-monsoon-r622093"),
 ("7th Cat Chinese Kitchen", "Leicester Square", "central", "chinese", 22, 7.8, 186, 50, "7th-cat-chinese-kitchen-at-empire-casino-r850980"),
 ("Blossom By Khans", "Battersea", "south", "indian", 25, 9.0, 266, 50, "blossom-by-khans-r744330"),
 ("Cinnamon Kitchen Battersea Power Station", "Battersea", "south", "indian", 25, 9.4, 702, 30, "cinnamon-kitchen-battersea-power-station-r600503"),
 ("The Sushi Co Walthamstow", "Walthamstow", "east", "sushi", 20, 9.2, 195, 40, "the-sushi-co-walthamstow-r847964"),
 ("Et House Swiss Cottage", "Swiss Cottage", "north", "mezze", 35, 9.6, 195, 20, "et-house-swiss-cottage-r826215"),
 ("The Sushi Co Streatham", "Streatham", "south", "sushi", 24, 9.1, 275, 40, "the-sushi-co-streatham-r815751"),
 ("Marhaba Kabul", "West Kensington", "west", "kebab", 30, 9.6, 30, 30, "marhaba-kabul-r864731"),
 ("Barcha Barcha", "Hammersmith", "west", "mezze", 30, 9.6, 25, 30, "barcha-barcha-r862796"),
 ("Hera", "Stratford", "east", "mezze", 35, 9.3, 235, 30, "hera-r831563"),
 ("Drawing Room at 11 Cadogan Gardens", "Chelsea", "west", "fine", 55, 9.2, 91, 30, "drawing-room-at-11-cadogan-gardens-r815696"),
]
for name, area, reg, c, price, score, cnt, pct, u in tf:
    style = 'casual' if price <= 25 else ('fancy' if price >= 45 else 'smart')
    v = venue(name, a=area + ", London", reg=reg, c=c, s=style, m=['l', 'd'])
    v['price'] = price
    if not v.get('ll') and GEO.get(area): v['ll'] = GEO[area]
    offer(v, p='thefork', u=TF + u, h='upto_food' if pct >= 40 else 'pct_food', n=pct, r=[score, cnt])

# ---------------- Code Hospitality (members, £4.99/month after free trial) ----------------
CODE = "https://www.codehospitality.co.uk/some-of-our-offers-on-code/"
code = [
 ("Plaza Khao Gaeng", "Tottenham Court Road, London", "central", "thai", "casual", ['l', 'd'], 'pct_food', 50),
 ("MEATliquor", "London, several sites", "multi", "burger", "casual", ['l', 'd'], 'pct_bill', 20),
 ("Sticks'n'Sushi", "London, several sites", "multi", "sushi", "smart", ['l', 'd'], 'pct_bill', 30),
 ("Rosa's Thai", "London, several sites", "multi", "thai", "casual", ['l', 'd'], 'pct_bill', 30),
 ("Grove House Tavern", "London", "multi", "british", "casual", ['d'], 'upto_bill', 50),
 ("Someday", "London", "multi", "cocktails", "smart", ['d'], 'pct_bill', 50),
 ("Cafe Boheme", "Soho, London", "central", "fine", "smart", ['b', 'l', 'd'], 'pct_bill', 30),
 ("The Blue Posts", "Soho, London", "central", "british", "casual", ['d'], 'pct_drinks', 20),
]
for name, area, reg, c, s, m, h, n in code:
    v = venue(name, a=area, reg=reg, c=c, s=s, m=m)
    if GEO.get(area): v['ll'] = GEO[area]
    offer(v, p='code', u=CODE, h=h, n=n)

# ---------------- tastecard (membership) ----------------
TC = "https://www.tastecard.co.uk/"
for name, c in [("PizzaExpress", "pizza"), ("ASK Italian", "italian"), ("Popeyes", "chicken"), ("Slug & Lettuce", "cocktails")]:
    v = venue(name, a="UK, many branches", reg='multi', ct='uk', c=c, s='casual', m=['l', 'd'])
    offer(v, p='tastecard', u=TC, h='two41', n=50)

# ---------------- Chains: official offers (via becleverwithyourcash.com, updated 28 Sep 2026) ----------------
def chain(name, c, m, s, u, x, n, end=None, d=None, k='dine', reg='multi', area="UK, many branches"):
    v = venue(name, a=area, reg=reg, ct='uk', c=c, s=s, m=m, k=k)
    o = dict(p='direct', u=u, h='text', x=x, n=n)
    if end: o['end'] = end
    if d: o['d'] = d
    offer(v, **o)

chain("PizzaExpress", "pizza", ['l', 'd'], 'casual', "https://www.pizzaexpress.com/one-pound-main",
      "Second pizza for £1", 45, end="2026-10-25", d="Classic and Leggera pizzas. Dine-in, delivery or collection, via the PizzaExpress Club app or website.")
chain("Frankie & Benny's", "burger", ['l', 'd'], 'casual', "https://www.frankieandbennys.com/one-pound-mains",
      "Second main for £1", 45, end="2026-10-02", d="Sunday to Friday, not Saturdays. Excludes Signature Grills and Classics. Sign up for the code.")
chain("Las Iguanas", "mexican", ['l', 'd'], 'casual', "https://www.iguanas.co.uk/one-pound-mains",
      "Second main for £1", 45, end="2026-09-30", d="Download the voucher from the website.")
chain("Bill's", "breakfast", ['b', 'l'], 'casual', "https://bills-website.co.uk/events/5-pancake-week/",
      "£5 pancake stacks", 30, end="2026-10-02", d="Any stack of buttermilk pancakes for £5. Book on the events page.")
chain("Mowgli Street Food", "indian", ['l', 'd'], 'casual', "https://www.mowglistreetfood.com/whats-on/",
      "Half-price curries on Mondays", 50, end="2026-09-28", d="Mondays in September, dine-in only. Excludes Mowgli chicken biryani.")
chain("IKEA Restaurant", "generic", ['b', 'l', 'd'], 'casual', "https://www.ikea.com/gb/en/ikea-family/",
      "Half-price food on Fridays", 50, d="For free IKEA Family members. Meatballs £2.45, fish & chips £3.45. Not at Hammersmith.")
chain("Five Guys", "burger", ['l', 'd'], 'casual', "https://fiveguys.co.uk/rewards/",
      "Free fries when you join", 20, d="Free Little or Regular fries on sign-up, plus a birthday treat.")
chain("Wagamama", "ramen", ['l', 'd'], 'casual', "https://www.wagamama.com/soul-club",
      "Free edamame or prawn crackers", 15, d="Join Soul Club in the app. Redeem when you spend £12.")
chain("LEON", "generic", ['b', 'l', 'd'], 'casual', "https://leon.co/club/",
      "30% off your next order", 30, d="Join the free LEON Lovers Club for the voucher.")
chain("Burger King", "burger", ['l', 'd'], 'casual', "https://www.burgerking.co.uk/rewards-policy",
      "Free Whopper with first app order", 40, d="First Click and Collect order over £3 in the app. Not at motorway services.")
chain("Burger King", "burger", ['l'], 'casual', "https://www.burgerking.co.uk/lunch-club",
      "£4.99 Lunch Club meal", 30, d="Lunch meal deal at participating restaurants.")
chain("McDonald's", "burger", ['b', 'l', 'd'], 'casual', "https://www.mcdonalds.com/gb/en-gb.html",
      "1,000 bonus points on first app order", 10, d="Worth £1 towards rewards in the MyMcDonald's app.")
chain("Meerkat Meals", "generic", ['d'], 'casual', "https://www.comparethemarket.com/customer-rewards/meerkat-meals/dine-out/",
      "2-for-1 meals, Sunday to Thursday", 50, d="Free for a year with a Compare the Market purchase. Covers many chains, like Prezzo and Côte.")

# ---------------- Independent spotlights (researched 28 Sep 2026) ----------------
tiki = venue("Grill Shack & Tiki Bar", key='grill-shack-tiki-bar', a="15 The Vale, East Acton, London W3 7SH", reg='west', ct='london',
             c='caribbean', s='smart', m=['d'])
tiki.update({'ll': [51.5066, -0.247], 'ig': 'https://www.instagram.com/tikibar15/', 'tt': 'https://www.tiktok.com/@tikibarlondon',
             'ph': '020 8616 2770', 'hrs': 'Wed–Thu 5–10pm · Fri–Sat 5–11pm · Sun 5–9:30pm · Mon–Tue closed', 'price': 35,
             'ins_fixed': ['gem', 'music', 'bar'],
             'mains': ["Griot – crispy marinated pork, fried plantain, pikliz", "Tasso – seasoned fried goat", "Legim – Haitian vegetable stew",
                       "Curry goat", "Jerk chicken", "BBQ sticky ribs", "Whole king prawns in Creole sauce", "Sea bass in tomato sauce",
                       "Fritay platter"],
             'celebs': ['Ed Sheeran', 'Rio Ferdinand', 'Gary Lineker', 'Jourdan Dunn', 'James McVey', 'Jamal Edwards'],
             'sumk': 'tiki', 'tg': ['Haitian'],
             'srcs': [['NW Londoner, Sep 2023', 'https://www.nwlondoner.co.uk/food-drink/27092023-humble-haitian-restaurant-in-east-acton-hotspot-for-celebs'],
                      ['Tripadvisor (4.6/5, 31 reviews)', 'https://www.tripadvisor.com/Restaurant_Review-g12592310-d17647761-Reviews-Grill_Shack_Tiki_Bar_London-Acton_Ealing_Greater_London_England.html'],
                      ['SquareMeal', 'https://www.squaremeal.co.uk/restaurants/tiki-bar-acton_30649'],
                      ['Eat Drink Travel, Apr 2023', 'https://www.eatdrinktravel.co.uk/single-post/grill-shack-and-tiki-bar']]})
offer(tiki, p='direct', u='https://www.instagram.com/tikibar15/', h='text', n=40, x="Bottomless drinks + starter + main, £45",
      d="London's only Haitian restaurant. Book by phone (020 8616 2770) or Instagram and ask for the £45 bottomless deal.")

# ---------------- Chicken, pizza, pasta, Caribbean and family chains (official pages, checked 28 Sep 2026) ----------------
chain("Nando's", "chicken", ['l', 'd'], 'casual', "https://www.nandos.co.uk/rewards",
      "Free food with Nando's Rewards", 25, d="One Chilli each day you spend £7 or more (eat in, collect or delivery). Rewards at 3, 6 and 10 Chillies.")
chain("KFC", "chicken", ['l', 'd'], 'casual', "https://www.kfc.co.uk/",
      "App deals every week", 30, d="Check the KFC app for this week's buckets and meal deals. Uber Eats also runs KFC offers.")
chain("Popeyes", "chicken", ['l', 'd'], 'casual', "https://popeyesuk.com/rewards",
      "Free Chicken Cruncher when you join", 30, d="Join Popeyes Rewards in the app and collect points on every order.")
chain("Wingstop", "chicken", ['l', 'd'], 'casual', "https://www.wingstop.co.uk/deals",
      "Wing deals in the app", 20, d="See the deals page and the Wingstop app for current offers near you.")
chain("Harvester", "chicken", ['l', 'd'], 'casual', "https://www.harvester.co.uk/offers",
      "£10 Chicken Tuesday, £10 Burger Wednesday", 35, d="For free Flavour Rewards members. Also 25% off food when you sign up.")
chain("Domino's", "pizza", ['l', 'd'], 'casual', "https://www.dominos.co.uk/deals",
      "Any pizza, any size, £8.99 on Mondays", 45, end="2026-10-19", d="App orders on Mondays. Collection deals also on the deals page.")
chain("Papa John's", "pizza", ['l', 'd'], 'casual', "https://www.papajohns.co.uk/",
      "Deals and student offers", 30, d="Check the Papa John's app for current codes, including student deals.")
chain("Pizza Hut", "pizza", ['l', 'd'], 'casual', "https://www.pizzahut.co.uk/deals",
      "Weekly delivery and collection deals", 30, d="See the deals page for your nearest Pizza Hut.")
chain("Bella Italia", "italian", ['l', 'd'], 'casual', "https://www.bellaitalia.co.uk/offers",
      "Second main for £1", 45, end="2026-10-02", d="Sunday to Friday. Sign up for the code. Kids eat free Sunday to Thursday. Students get 40% off food until 31 Oct.")
chain("Zizzi", "italian", ['l', 'd'], 'casual', "https://www.zizzi.co.uk/offers",
      "30% off food", 30, end="2026-10-16", d="Join the free Zillionaires' Club. All day Monday to Friday. Free garlic bread on sign-up.")
chain("Chiquito", "mexican", ['l', 'd'], 'casual', "https://www.chiquito.co.uk/offers",
      "40% off food for students", 40, end="2026-10-31", d="Lunch set menu from £9.95. 30% off mains with a cinema ticket.")
chain("TGI Fridays", "burger", ['l', 'd'], 'casual', "https://www.tgifridays.co.uk/promotions",
      "2-for-1 cocktails", 50, d="Also 10% off every visit when you keep your receipt, and app, main and drink from £12.49.")
chain("Turtle Bay", "caribbean", ['l', 'd'], 'casual', "https://www.turtlebay.co.uk/happy-hour",
      "2-for-1 cocktails, all day", 50, d="Caribbean restaurant. Happy hour offer at every Turtle Bay.")
chain("Toby Carvery", "breakfast", ['b', 'l', 'd'], 'casual', "https://www.tobycarvery.co.uk/offers",
      "All-you-can-eat breakfast £6.99", 30, d="Monday to Friday, £7.49 at weekends. Join Carvery Club for 25% off food.")
chain("German Doner Kebab", "kebab", ['l', 'd'], 'casual', "https://gdk.com/uk/",
      "£5 Fridays and 2-for-1 Tuesdays", 50, d="Check your local GDK and the app for times.")
chain("Krispy Kreme", "breakfast", ['b', 'l'], 'casual', "https://www.krispykreme.co.uk/",
      "24 doughnuts for £20 on Wednesdays", 30, d="In store. Check the Krispy Kreme app for other rewards.")

# ---------------- Coffee & breakfast loyalty ----------------
chain("Pret A Manger", "coffee", ['b', 'l'], 'casual', "https://www.pret.co.uk/en-GB/club-pret",
      "Up to 5 drinks a day for £30 a month", 60, k='coffee', d="Club Pret subscription in the app. First month is often free.")
chain("Greggs", "breakfast", ['b', 'l'], 'casual', "https://www.greggs.com/app",
      "Free drink when you join the app", 30, k='coffee', d="Then collect stamps for free items.")
chain("Costa Coffee", "coffee", ['b'], 'casual', "https://www.costa.co.uk/costa-club",
      "Free drink after 8 beans", 12, k='coffee', d="Costa Club app. Bonus beans with a reusable cup, plus birthday cake.")
chain("Caffè Nero", "coffee", ['b'], 'casual', "https://caffenero.com/uk/",
      "10th drink free", 10, k='coffee', d="Collect stamps in the app. Extra stamp with a reusable cup.")
chain("GAIL's Bakery", "coffee", ['b'], 'casual', "https://gails.com/pages/loyalty",
      "Free drink or loaf after 9 stamps", 10, k='coffee', d="GAIL's app, plus a birthday treat.")
chain("Starbucks", "coffee", ['b'], 'casual', "https://www.starbucks.co.uk/rewards",
      "Free drink at 150 Stars", 5, k='coffee', d="3 Stars per £1 in the Starbucks Rewards app.")
chain("LEON Roast Rewards", "coffee", ['b'], 'casual', "https://leon.co/club/",
      "Up to 5 barista drinks a day for £25 a month", 60, k='coffee')

# ---------------- Delivery apps ----------------
def deliv(name, p, u, x, n, d, end=None, c='delivery'):
    v = venue(name, a="Delivery, UK-wide", reg='multi', ct='uk', c=c, s='casual', m=['l', 'd'], k='delivery')
    o = dict(p=p, u=u, h='text', x=x, n=n, d=d)
    if end: o['end'] = end
    offer(v, **o)

deliv("Deliveroo Plus Silver", 'deliveroo', "https://deliveroo.co.uk/plus",
      "Free delivery, free with Amazon Prime", 25, "Free delivery on £15+ restaurant and £25+ grocery orders. Also free for students (UNiDAYS) and Blue Light Card holders.")
deliv("Deliveroo offers", 'deliveroo', "https://deliveroo.co.uk/",
      "Up to 50% off weekend takeaways", 50, "Selected customers get codes for 30% to 50% off (max £15, min £20). Check the Offers tab in your app.", end="2026-10-11")
deliv("Uber One", 'ubereats', "https://www.ubereats.com/gb/uber-one",
      "3 months free, then £4.99 a month", 30, "Unlimited free delivery on eligible restaurant and grocery orders, plus member discounts.")
deliv("PizzaExpress on Uber Eats", 'ubereats', "https://www.ubereats.com/gb/search?q=PizzaExpress",
      "40% off selected favourites", 40, "Seen on Uber Eats in September 2026. Check the app for the current dishes.", c='pizza')
deliv("PizzaExpress on Just Eat", 'justeat', "https://www.just-eat.co.uk/",
      "50% off selected items", 50, "Seen on Just Eat in September 2026. Search PizzaExpress in the app.", c='pizza')
deliv("Just Eat new customers", 'justeat', "https://www.just-eat.co.uk/",
      "£10 off your first 3 orders", 40, "New app customers, minimum spend £15.", end="2026-09-30")
deliv("Just Eat+", 'justeat', "https://www.just-eat.co.uk/",
      "Free delivery for £5.99 per 90 days", 20, "Free delivery on eligible orders over £15. Service fees still apply.")

# ---------------- Groceries ----------------
def grocery(name, u, x, n, d, c='grocery'):
    v = venue(name, a="UK-wide", reg='multi', ct='uk', c=c, s='casual', m=[], k='grocery')
    offer(v, p='direct', u=u, h='text', x=x, n=n, d=d)

grocery("Too Good To Go", "https://www.toogoodtogo.com/en-gb", "Surprise bags at about a third of the price", 66,
        "Unsold food from cafés, bakeries, restaurants and supermarkets near you, all over the UK. Greggs, Costa, Morrisons and Co-op use it too. Reserve in the app, collect the same day.")
grocery("Olio", "https://olioapp.com/en/", "Free food from neighbours and shops", 100, "Surplus food shared for free, UK-wide. Collect locally.")
grocery("Gander", "https://www.gander.co/", "Find reduced-to-clear food near you", 50,
        "Free app that shows yellow-sticker bargains in local supermarkets and shops before you go.")
grocery("Approved Food", "https://approvedfood.co.uk/", "Short-date and surplus groceries online", 50,
        "Big brands at low prices, delivered anywhere in the UK. Check best-before dates when you order.")
grocery("Tesco Clubcard", "https://www.tesco.com/clubcard", "Clubcard Prices on thousands of items", 20,
        "Free to join. Points worth 1p each, doubled with Reward Partners.")
grocery("Sainsbury's Nectar", "https://www.sainsburys.co.uk/nectar", "Nectar Prices and personal offers", 15, "Free to join. About 0.5p per point.")
grocery("Lidl Plus", "https://www.lidl.co.uk/c/lidl-plus/s10023095", "Weekly coupons in the app", 15, "Free app. Points per £1 spent and personal own-brand vouchers.")
grocery("Co-op Membership", "https://www.coop.co.uk/membership", "Member Prices on hundreds of lines", 15, "£1 to join. Co-op says members save up to £300 a year.")
grocery("Morrisons More", "https://my.morrisons.com/more/", "5 points per £1 plus More Prices", 10, "Free to join. Straight discounts on big brands.")
grocery("Waitrose myWaitrose", "https://www.waitrose.com/ecom/mywaitrose", "Weekly vouchers and 20% off selected counters", 20, "Free to join, with free hot drinks offers.")
grocery("Asda Rewards", "https://www.asda.com/rewards", "Cashback on Star Products", 10, "Free app. Cashback goes into your Cashpot to spend in store.")
grocery("Deliveroo Grocery", "https://deliveroo.co.uk/", "50% off your first grocery order", 50,
        "Max £10 off, minimum £15. For customers new to Deliveroo grocery. Code in the app.")

# ---------- TableFifty Score + "Perfect for" insights ----------
# Score: Bayesian average of the diner ratings we can use (First Table, TheFork), on a 10-point scale.
# Few reviews pull a place towards 8.0, so a 10/10 from 3 people never beats 9.5 from 800. Google data is never mixed in (Google terms).
PRIOR, WEIGHT = 8.0, 20
INS = [('date', {'Date night'}), ('occasion', {'Special occasion'}), ('gem', {'Hidden gems'}), ('views', {'Views', 'Waterfront'}),
       ('music', {'Live music'}), ('late', {'Late night'}), ('business', {'Business meetings'}), ('bar', {'Bar scene', 'Cocktail bar', 'Wine bar'}),
       ('garden', {'Beer garden'}), ('dog', {'Dog friendly'}), ('private', {'Private dining'}), ('halal', {'Halal'}),
       ('vegan', {'Vegan options'}), ('gf', {'Gluten Free options'}), ('kids', {'Kids', 'Child friendly'}), ('groups', {'Groups'}), ('families', {'Families'})]
COMMON = {'vegan', 'gf', 'kids', 'groups', 'families'}
RC_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'review_counts.json')
try: RC = json.load(open(RC_FILE))
except Exception: RC = {'day': None, 'base': {}, 'last': {}}
TODAY = datetime.date.today().isoformat()
if RC.get('day') != TODAY: RC = {'day': TODAY, 'base': RC.get('last', {}), 'last': RC.get('last', {})}
counts_now = {}
for v in V.values():
    rs = [o['r'] for o in v['o'] if o.get('r')]
    n = sum(r[1] for r in rs)
    if n >= 10:
        score = (sum(r[0] * r[1] for r in rs) + PRIOR * WEIGHT) / (n + WEIGHT)
        src = sorted({('ft' if (len(r) > 2 and r[2] == 'ft') else 'tf') for r in rs})
        v['sc'] = [round(score, 1), n, ','.join(src)]
        counts_now[v['id']] = n
        if RC['base'].get(v['id']) is not None and n > RC['base'][v['id']]: v['nr'] = n - RC['base'][v['id']]
    tags = v.pop('_tags', set())
    ins = [k for k, names in INS if tags & names] + v.pop('ins_fixed', [])
    rare = [k for k in ins if k not in COMMON]
    pick = (rare + [k for k in ins if k in COMMON])[:3]
    if v.get('sc') and v['sc'][0] >= 9.3 and v['sc'][1] >= 100: pick = ['loved'] + pick[:2]
    if pick: v['ins'] = pick
RC['last'] = counts_now
json.dump(RC, open(RC_FILE, 'w'), separators=(',', ':'))

# ---------- finalise ----------
out = []
for v in V.values():
    v.pop('_tags', None)
    if not v['m'] and v['k'] in ('dine', 'coffee'): v['m'] = ['l', 'd']
    out.append(v)
CITIES = {}
for c, pts in CITY_PTS.items():
    CITIES[c] = {'n': CITY_NAMES[c], 'll': [round(statistics.median(p[0] for p in pts), 4), round(statistics.median(p[1] for p in pts), 4)]}
if 'london' in CITIES: CITIES['london']['ll'] = [51.5074, -0.1278]
PCA = {k: v for k, v in json.load(open(os.path.join(HERE, 'pc_areas.json'))).items() if v}
for v in out:
    if v['reg'] == v.get('ct') and v['ct'] != 'london': v.pop('reg')
CHECKED = max([SEEN] + [r.get("checked") or SEEN for r in PAGES.values()])
js = ("const DEALS_CHECKED = " + json.dumps(CHECKED) + ";\nconst CITIES = " + json.dumps(CITIES, ensure_ascii=False, separators=(',', ':')) +
      ";\nconst PC_AREAS = " + json.dumps(PCA, ensure_ascii=False, separators=(',', ':')) +
      ";\nconst DEALS = " + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ";\n")
open(os.path.join(HERE, 'deals.js'), 'w', encoding='utf-8').write(js)
print(len(out), 'venues,', sum(len(v['o']) for v in out), 'offers')
from collections import Counter
print(Counter(v['k'] for v in out)); print(Counter(o['p'] for v in out for o in v['o'])); print(Counter(v['ct'] for v in out).most_common())
print(Counter(v['c'] for v in out).most_common()); print(len(js), 'bytes')
