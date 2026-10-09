"""PHASE PULSE conservative beta, adapted from pokemon-restock (MIT)
and Travis-ML/target-stock-monitor (MIT). Python 3.11+, stdlib only.
No cookies, proxy rotation, browser impersonation or block bypass.
"""
import argparse, datetime as dt, hashlib, html, json, os, pathlib, re, time
import urllib.request, urllib.parse, urllib.error, uuid
ROOT = pathlib.Path(__file__).resolve().parent
STATE = ROOT / 'state.json'
REPORT = ROOT / 'report.json'
KEY = '9f36aeafbe60771e321a7cc95a78140772ab3e96'  # Public frontend key; not a credential.
BASE = 'https://redsky.target.com/redsky_aggregations/v1/web/'
VISITOR = str(uuid.uuid4())
class CheckError(Exception):
    def __init__(self, message, pause=False):
        super().__init__(message); self.pause = pause
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None

def now(): return dt.datetime.now(dt.timezone.utc).isoformat()
def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp'); tmp.write_text(json.dumps(data, indent=2)); tmp.replace(path)
def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default

def request(url, payload=None):
    headers = {'User-Agent': 'PHASE-PULSE-Beta/0.1', 'Accept': 'application/json,text/html'}
    if payload is not None: headers['Content-Type'] = 'application/json'
    req = urllib.request.Request(url, data=json.dumps(payload).encode() if payload is not None else None, headers=headers)
    try:
        with urllib.request.build_opener(NoRedirect).open(req, timeout=25) as r:
            body = r.read(5_000_001)
            if len(body)>5_000_000: raise CheckError('Response exceeds size limit')
            text = body.decode('utf-8')
    except urllib.error.HTTPError as e:
        raise CheckError('HTTP '+str(e.code), e.code in (401,403,412,429,435)) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise CheckError('Network request failed; no automatic retry') from None
    if payload is None and re.search(r'<title[^>]*>[^<]*(robot or human|access denied)|verify you are human|px-captcha',text,re.I):
        raise CheckError('Retailer access challenge; manual review required', True)
    return text

def folded(s):
    import unicodedata
    return ''.join(c for c in unicodedata.normalize('NFD',html.unescape(s).lower()) if unicodedata.category(c)!='Mn')
def matches(name, cfg): return any(k in folded(name) for k in cfg['include_keywords'])
def valid_url(url, retailer):
    p=urllib.parse.urlparse(url)
    return p.scheme=='https' and p.hostname in (retailer+'.com','www.'+retailer+'.com') and not p.username

def target_get(endpoint, params, cfg):
    args={'key':KEY,'visitor_id':VISITOR,'store_id':cfg['target_store_id'],'pricing_store_id':cfg['target_store_id'],'zip':cfg['target_zip'],'channel':'WEB',**params}
    try: return json.loads(request(BASE+endpoint+'?'+urllib.parse.urlencode(args)))
    except ValueError: raise CheckError('Invalid Target JSON') from None

def target_status(fulfillment):
    shipping=fulfillment.get('shipping_options') if isinstance(fulfillment,dict) else None
    s=shipping.get('availability_status') if isinstance(shipping,dict) else None
    return {'IN_STOCK':'in_stock','OUT_OF_STOCK':'out_of_stock','PRE_ORDER_SELLABLE':'pre_order','PRE_ORDER_UNSELLABLE':'pre_order_unavailable','UNAVAILABLE':'unavailable'}.get(s,'unknown')

def walmart_status(item):
    av=item.get('availabilityStatusV2',{}).get('value')
    if item.get('isOutOfStock') is True or av=='OUT_OF_STOCK': return 'out_of_stock'
    if av=='IN_STOCK' and item.get('isOutOfStock') is not True:
        return 'pre_order' if item.get('preOrder',{}).get('isPreOrder') is True else 'in_stock'
    return 'unknown'  # Never infer inventory from missing fields or an Add to cart flag.

def walmart_parse(text,cfg):
    m=re.search(r'<script[^>]+id=["\x27]__NEXT_DATA__["\x27][^>]*>([\s\S]*?)</script>',text,re.I)
    if not m: raise CheckError('Walmart structured data missing; inventory unknown')
    try:
        d=json.loads(m[1]); stacks=d['props']['pageProps']['initialData']['searchResult']['itemStacks']
    except (ValueError,KeyError,TypeError): raise CheckError('Walmart response schema changed') from None
    products=[]; raw_count=0
    for stack in stacks:
        for item in stack.get('items',[]):
            if not item.get('usItemId'):continue
            raw_count+=1
            if item.get('sellerName')!='Walmart.com':continue
            name=item.get('name','')
            if not matches(name,cfg):continue
            url=urllib.parse.urljoin('https://www.walmart.com',item.get('canonicalUrl','').split('?')[0])
            if not valid_url(url,'walmart') or not url.startswith('https://www.walmart.com/ip/'):continue
            products.append({'id':str(item['usItemId']),'name':name,'url':url,'status':walmart_status(item),'seller':'Walmart.com','checked_at':now(),'evidence':'retailer_search_availability','price':item.get('price')})
    if not raw_count:raise CheckError('No product records; empty search is not an inventory check')
    return products,raw_count

def check_walmart(cfg,old):
    products={};raw=0
    for term in cfg['search_keywords']:
        rows,count=walmart_parse(request('https://www.walmart.com/search?'+urllib.parse.urlencode({'q':term,'page':1})),cfg)
        raw+=count;products.update({p['id']:p for p in rows});time.sleep(cfg['request_spacing_seconds'])
    return list(products.values()),raw

def check_target(cfg,old):
    import discovery
    if cfg.get('paused_retailers',{}).get('target'):
        raise CheckError(cfg['paused_retailers']['target'],True)
    try: discovery.collect(cfg,old,target_get,now,time.sleep)
    except (ValueError,CheckError) as exc:
        # Discovery and known-product inventory are complementary. A malformed
        # search page or ordinary network failure must not disable saved TCINs.
        # Access challenges are different: stop ALL Target traffic immediately.
        if isinstance(exc,CheckError) and exc.pause:raise
        old.setdefault('discovery',{})['last_error']=str(exc)
        old['discovery']['last_run']={**old['discovery'].get('last_run',{}),'status':'error'}
    ids=discovery.select_watchlist(cfg,old);products=[]
    for tcin in ids:
        metadata=old.get('discovery',{}).get('products',{}).get(tcin) or old.get('products',{}).get(tcin)
        if not metadata or not valid_url(metadata.get('url',''),'target'):
            raise CheckError('Target metadata not verified for TCIN '+tcin)
        if not re.fullmatch(r'\d{7,10}',str(tcin)):raise CheckError('Invalid Target TCIN')
        d=target_get('product_fulfillment_and_variation_hierarchy_v1',{'tcin':tcin,'page':'/p/A-'+tcin},cfg)
        data=d.get('data') if isinstance(d,dict) else None
        product=data.get('product') if isinstance(data,dict) else None
        if not isinstance(product,dict):raise CheckError('Target product response schema changed')
        if str(product.get('tcin'))!=tcin or not isinstance(product.get('fulfillment'),dict):raise CheckError('Target fulfillment missing')
        fulfillment=product['fulfillment']
        products.append({'id':tcin,'name':metadata['name'],'url':metadata['url'],
            'status':target_status(fulfillment),'checked_at':now(),
            'source_status':(fulfillment.get('shipping_options') or {}).get('availability_status') if isinstance(fulfillment.get('shipping_options'),dict) else None,
            'evidence':'shipping_options.availability_status','price':metadata.get('price'),'image':metadata.get('image')})
        time.sleep(max(2,cfg.get('request_spacing_seconds',2)))
    return products,len(ids)

def merge(old,rows,retailer):
    events=[];products=old.setdefault('products',{})
    for p in rows:
        previous=products.get(p['id']); status=p['status']
        if status=='unknown':continue  # Retain prior evidence, never manufacture a transition.
        if previous and ((previous['status'] in ('out_of_stock','unavailable','pre_order_unavailable','pre_order') and status=='in_stock') or (previous['status'] in ('out_of_stock','unavailable','pre_order_unavailable') and status=='pre_order')):
            key=hashlib.sha256((retailer+p['id']+previous['checked_at']+status).encode()).hexdigest()[:24]
            events.append({'event_id':key,'kind':'preorder_open' if status=='pre_order' else 'restock','retailer':retailer,'product':p,'previous_status':previous['status'],'delivery':'pending','created_at':now()})
        products[p['id']]=p  # Newly observed products silently baseline, even after initial run.
    return events

def check(cfg,state):
    report={'checked_at':now(),'retailers':{},'alerts_sent':0}
    for retailer,fn in [('target',check_target),('walmart',check_walmart)]:
        old=state.setdefault(retailer,{'products':{}})
        configured_pause=cfg.get('paused_retailers',{}).get(retailer)
        if configured_pause:
            report['retailers'][retailer]={'status':'paused','reason':configured_pause,'last_success':old.get('last_success')};continue
        if old.get('paused'):
            report['retailers'][retailer]={'status':'paused','reason':old['paused']};continue
        try:
            rows,raw=fn(cfg,old)
            known=[p for p in rows if p['status']!='unknown']
            events=merge(old,rows,retailer)
            state.setdefault('outbox',[]).extend(events)
            if known:old['last_success']=now()
            old['last_error']=None
            report['retailers'][retailer]={'status':'ok' if known else 'no_verified_inventory','products_checked':len(known),'records_retrieved':raw,'baseline_total':len(old['products']),'in_stock':sum(p['status']=='in_stock' for p in known),'new_restock_events':len(events),'last_success':old.get('last_success')}
            if retailer=='target':
                report['retailers'][retailer]['discovery']=old.get('discovery',{}).get('last_run',{})
                if old.get('discovery',{}).get('last_error'):
                    report['retailers'][retailer].update(status='partial' if known else 'error',discovery_error=old['discovery']['last_error'])
        except CheckError as e:
            old['last_error']=str(e)
            if e.pause:old['paused']=str(e)
            report['retailers'][retailer]={'status':'paused' if e.pause else 'error','reason':str(e),'last_success':old.get('last_success')}
    report['new_listing_events_queued']=queue_discoveries(state)
    write(STATE,state);write(REPORT,report);print(json.dumps(report,indent=2))
    return 0 if all(r['status']=='ok' for r in report['retailers'].values()) else 1

def queue_discoveries(state):
    """Use the existing durable outbox; replaying the discovery journal is safe."""
    outbox=state.setdefault('outbox',[]);known={e['event_id'] for e in outbox};count=0
    for e in state.get('target',{}).get('discovery',{}).get('events',[]):
        if e['event_id'] in known:continue
        # Old journals predate notification support. Do not replay old catalog events.
        if e.get('notification_version')!=1:continue
        p={'id':e['tcin'],'name':e['name'],'url':e['url'],'price':e.get('price'),
           'image':e.get('image'),'seller':e.get('seller','unknown'),'status':'unknown',
           'checked_at':e['observed_at'],'evidence':'Target search listing; availability unverified'}
        outbox.append({'event_id':e['event_id'],'kind':'new_listing','retailer':'target',
                       'product':p,'previous_status':'not previously tracked','delivery':'pending',
                       'created_at':e['observed_at']})
        known.add(e['event_id']);count+=1
    return count

def alert_payload(event):
    p=event['product'];kind=event.get('kind','restock')
    labels={'new_listing':'NEW TO MONITOR','preorder_open':'PREORDER OPEN','restock':'RESTOCK'}
    descriptions={'new_listing':'Relevant listing newly found by PHASE. Availability and retailer publication date are unverified.',
                  'preorder_open':'Retailer reports preorder availability. Availability can change.',
                  'restock':'Retailer reports in stock. Availability can change.'}
    fields=[{'name':'Retailer','value':event['retailer']},
            {'name':'TCIN' if event['retailer']=='target' else 'Product ID','value':str(p['id'])},
            {'name':'Price','value':str(p.get('price') or 'Not provided by source')[:1024]},
            {'name':'Evidence','value':p['evidence']},
            {'name':'Previous status','value':event['previous_status']}]
    if kind=='new_listing':fields.append({'name':'Seller classification','value':p.get('seller','unknown')})
    embed={'title':(labels[kind]+' • '+p['name'])[:256],'url':p['url'],
           'description':descriptions[kind],'timestamp':p['checked_at'],'fields':fields,
           'footer':{'text':'PHASE PULSE BETA • '+event['event_id']}}
    image=p.get('image')
    if isinstance(image,str) and urllib.parse.urlsplit(image).scheme=='https' and urllib.parse.urlsplit(image).hostname=='target.scene7.com':
        embed['thumbnail']={'url':image}
    return {'username':'PHASE PULSE • BETA','allowed_mentions':{'parse':[]},'embeds':[embed]}

def webhook(retailer):
    url=os.environ.get('DISCORD_'+retailer.upper()+'_WEBHOOK_URL','')
    if not re.fullmatch(r'https://discord\.com/api/webhooks/\d+/[A-Za-z0-9_-]+',url):raise CheckError('Missing or invalid '+retailer+' webhook secret')
    return url

def reserve(cfg,state):
    token=os.environ.get('PULSE_RUN_ID')
    if not token:raise CheckError('PULSE_RUN_ID required for durable delivery reservations')
    reserved=0
    for event in state.get('outbox',[]):
        if event['delivery']=='pending' and reserved<cfg['max_alerts_per_run']:
            # Validate the secret before consuming a notification.
            webhook(event['retailer'])
            event['delivery']='reserved';event['reservation']=token;reserved+=1
    write(STATE,state);print(json.dumps({'reserved':reserved}));return 0

def deliver(cfg,state):
    # An ambiguous result is held for review, never blindly retried.
    sent=0
    for event in state.get('outbox',[]):
        if event['delivery']!='reserved' or event.get('reservation')!=os.environ.get('PULSE_RUN_ID') or sent>=cfg['max_alerts_per_run']:continue
        p=event['product']
        if (dt.datetime.now(dt.timezone.utc)-dt.datetime.fromisoformat(p['checked_at'])).total_seconds()>900:
            event['delivery']='expired';continue
        url=webhook(event['retailer'])
        event['delivery']='attempting';write(STATE,state)
        payload=alert_payload(event)
        try:
            result=json.loads(request(url+'?wait=true',payload));event['discord_message_id']=result['id'];event['delivery']='sent';sent+=1
        except (CheckError,ValueError,KeyError):event['delivery']='uncertain';write(STATE,state);raise CheckError('Discord delivery uncertain; manual review, no auto-retry') from None
        write(STATE,state);time.sleep(2)
    write(STATE,state);print(json.dumps({'alerts_sent':sent}));return 0

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['check','reserve','deliver']);args=ap.parse_args()
    cfg=load(ROOT/'config.json',{});state=load(STATE,{'outbox':[]})
    try:raise SystemExit({'check':check,'reserve':reserve,'deliver':deliver}[args.mode](cfg,state))
    except CheckError as e:print(str(e));raise SystemExit(1)
