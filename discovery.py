"""Target discovery adapted conceptually from pokemon-restock's MIT-declared
search pagination, TCIN normalization and first-seen tracking. No stock inference.
"""
import copy, hashlib, html, re, unicodedata
from urllib.parse import urlsplit

def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFD', html.unescape(str(value)).lower()) if unicodedata.category(c)!='Mn')

def normalize(raw, cfg, observed_at):
    item=raw.get('item',{})
    tcin=str(raw.get('tcin') or item.get('tcin') or '')
    name=html.unescape(item.get('product_description',{}).get('title',''))
    if not re.fullmatch(r'\d{7,10}',tcin) or not name:return None
    category=item.get('product_classification',{}).get('item_type',{}).get('name','')
    include=cfg.get('include_keywords',[]); exclude=cfg.get('exclude_keywords',[])
    if not include or not any(fold(k) in fold(name) for k in include):return None
    if any(fold(k) in fold(name) for k in exclude):return None
    allowed=cfg.get('target_discovery_categories',[])
    if allowed and category and not any(fold(k) in fold(category) for k in allowed):return None
    url=item.get('enrichment',{}).get('buy_url','')
    if url.startswith('/'):url='https://www.target.com'+url
    parts=urlsplit(url)
    if parts.scheme!='https' or parts.hostname not in ('target.com','www.target.com') or parts.username or parts.password or parts.port not in (None,443):return None
    if not re.search(r'/A-'+tcin+r'(?:/|$)',parts.path):return None
    url=parts._replace(query='',fragment='').geturl()
    marketplace=item.get('fulfillment',{}).get('is_marketplace')
    relation=item.get('relationship_type','')
    seller='marketplace' if marketplace is True or relation.startswith('TargetPlus') else 'target' if marketplace is False else 'unknown'
    return {'id':tcin,'name':name,'url':url,'category':category,'seller':seller,
            'eligible_for_inventory':seller=='target','discovered_at':observed_at,
            'last_seen':observed_at,'source':'target_search','inventory_status':'unknown'}

def parse_page(data,cfg,observed_at):
    search=data.get('data',{}).get('search',{})
    rows=search.get('products')
    if not isinstance(rows,list):raise ValueError('Target discovery response schema changed')
    products={}
    for row in rows:
        if not isinstance(row,dict):raise ValueError('Malformed Target product record')
        try:p=normalize(row,cfg,observed_at)
        except (TypeError,AttributeError,ValueError):p=None
        if p:products[p['id']]=p
    total=search.get('search_response',{}).get('metadata',{}).get('total_results')
    return list(products.values()),len(rows),total

def absorb(discovery,rows,scope,observed_at):
    """First observation per query/page silently baselines; later new IDs journal once.
    A missing record is neither removed nor marked seen. Scope baselines prevent a
    new keyword/page from relabeling an old catalog as newly listed by Target.
    """
    products=discovery.setdefault('products',{}); scopes=discovery.setdefault('baselined_scopes',[])
    is_baseline=scope not in scopes; events=[]
    for row in rows:
        tcin=row['id'];old=products.get(tcin)
        first=old['first_seen'] if old else observed_at
        products[tcin]={**copy.deepcopy(row),'first_seen':first,'last_seen':observed_at}
        if not old and not is_baseline:
            key=hashlib.sha256(('target:new_listing:'+tcin).encode()).hexdigest()[:24]
            events.append({'event_id':key,'kind':'new_listing','retailer':'target','tcin':tcin,
                           'name':row['name'],'url':row['url'],'observed_at':observed_at,
                           'inventory_status':'unknown','note':'New to this monitor; retailer publication date unknown'})
    if is_baseline:scopes.append(scope)
    journal=discovery.setdefault('events',[]);known={e['event_id'] for e in journal}
    journal.extend(e for e in events if e['event_id'] not in known)
    return events

def select_watchlist(cfg,old):
    """Automatically track eligible discovered TCINs; rotate bounded checks fairly."""
    discovered=old.get('discovery',{}).get('products',{})
    ids=list(dict.fromkeys(cfg.get('target_tcins',[])+list(old.get('products',{}))+[
        tcin for tcin,p in discovered.items() if p['eligible_for_inventory']]))
    ids=[i for i in ids if discovered.get(i,{}).get('seller')!='marketplace']
    if not ids:return []
    cursor=old.get('inventory_cursor',0)%len(ids);limit=max(1,int(cfg.get('max_target_products',12)))
    selected=(ids[cursor:]+ids[:cursor])[:limit]
    old['inventory_cursor']=(cursor+len(selected))%len(ids)
    return selected

def collect(cfg,old,fetch,clock,sleep):
    discovery=old.setdefault('discovery',{})
    terms=list(dict.fromkeys(cfg.get('search_keywords',[])))
    pages=max(1,min(int(cfg.get('search_pages',1)),3))
    budget=max(1,min(int(cfg.get('target_discovery_request_budget',len(terms))),15))
    scopes=[(term,page) for term in terms for page in range(pages)]
    if not scopes:raise ValueError('No discovery keywords configured')
    cursor=discovery.get('cursor',0)%len(scopes); requests=0;seen=set();new=0;raw=0
    try:
        for i in range(min(budget,len(scopes))):
            term,page=scopes[(cursor+i)%len(scopes)];stamp=clock()
            data=fetch('plp_search_v2',{'keyword':term,'count':24,'offset':page*24,
                'default_purchasability_filter':'false','page':'/search','platform':'desktop'},cfg)
            rows,count,total=parse_page(data,cfg,stamp)
            scope=repr((term,page));events=absorb(discovery,rows,scope,stamp)
            requests+=1;raw+=count;seen.update(p['id'] for p in rows);new+=len(events)
            discovery.update(cursor=(cursor+i+1)%len(scopes),last_success=stamp,last_error=None)
            if i+1<min(budget,len(scopes)):sleep(max(2,cfg.get('request_spacing_seconds',2)))
    except Exception as exc:
        discovery['last_error']=str(exc)
        discovery['last_run']={'status':'error','pages_completed':requests,'records_retrieved':raw}
        raise
    result={'status':'ok','pages_completed':requests,'records_retrieved':raw,'relevant_seen':len(seen),
            'tracked_discoveries':len(discovery['products']),'new_listing_events':new,
            'eligible_target_sold':sum(p['eligible_for_inventory'] for p in discovery['products'].values())}
    discovery['last_run']=result
    return result
