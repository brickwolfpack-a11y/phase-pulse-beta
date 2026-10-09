"""Manual, isolated verification. Never changes production stock baseline."""
import contextlib, copy, hashlib, io, json, os, pathlib, re, subprocess, sys, tempfile
import urllib.error, urllib.parse, urllib.request
import pulse
ROOT=pathlib.Path(__file__).resolve().parent
LEDGER=ROOT/'verification.json'
EXPECTED={'target':'1557676686143656007','walmart':'1557676779651473448'}

def save(d): pulse.write(LEDGER,d)
def persist():
    subprocess.run(['git','add','verification.json'],check=True)
    if subprocess.run(['git','diff','--cached','--quiet']).returncode:
        subprocess.run(['git','commit','-m','Persist isolated PHASE verification evidence [skip ci]'],check=True)
        subprocess.run(['git','push','origin','HEAD:main'],check=True)

def tests(d):
    cfg=pulse.load(ROOT/'config.json',{})
    real=pulse.load(ROOT/'state.json',{})
    d.setdefault('tests',{})
    for retailer,channel in EXPECTED.items():
        entry=d['tests'].setdefault(retailer,{})
        if entry.get('attempted'):
            print(retailer+': prior delivery attempt retained; no repeat');continue
        p=copy.deepcopy(next(iter(real[retailer]['products'].values())))
        p.update(status='out_of_stock',checked_at=pulse.now(),evidence='SIMULATED TEST — NOT RETAILER INVENTORY')
        isolated={'products':{}}
        assert not pulse.merge(isolated,[copy.deepcopy(p)],retailer)
        assert not pulse.merge(isolated,[copy.deepcopy(p)],retailer)
        p.update(status='in_stock',checked_at=pulse.now())
        events=pulse.merge(isolated,[copy.deepcopy(p)],retailer)
        assert len(events)==1
        assert not pulse.merge(isolated,[copy.deepcopy(p)],retailer)
        assert not pulse.merge(isolated,[copy.deepcopy(p)],retailer)
        entry.update(duplicate_logic='PASS',simulated_transition='PASS',attempted=pulse.now(),delivery='reserved',expected_channel=channel)
        save(d);persist() # Durable one-time attempt before webhook call.
        with tempfile.TemporaryDirectory() as tmp:
            original_state=pulse.STATE;original_request=pulse.request
            pulse.STATE=pathlib.Path(tmp)/'isolated-state.json'
            isolated_state={'outbox':events}
            observed={};posts=[]
            def labeled_request(url,payload=None):
                if payload is not None:
                    posts.append(1)
                    payload=copy.deepcopy(payload)
                    embed=payload['embeds'][0]
                    embed['title']='TEST ONLY — '+retailer.upper()+' delivery + simulated transition'
                    embed['description']='CONTROLLED TEST: simulated OUT_OF_STOCK → IN_STOCK. This is NOT a genuine restock and does NOT verify live retailer retrieval. No purchase action is implied.'
                    embed['footer']['text']='PHASE PULSE TEST • '+events[0]['event_id']
                    payload['username']='PHASE PULSE • TEST'
                response=original_request(url,payload)
                if payload is not None:
                    received=json.loads(response)
                    observed.update(message_id=received.get('id'),channel_id=received.get('channel_id'))
                return response
            pulse.request=labeled_request
            try:
                with contextlib.redirect_stdout(io.StringIO()):
                    pulse.reserve(cfg,isolated_state)
                    pulse.deliver(cfg,isolated_state)
                assert observed.get('message_id') and observed.get('channel_id')==channel
                # Same reserved event cannot deliver twice after success.
                with contextlib.redirect_stdout(io.StringIO()):
                    pulse.deliver(cfg,isolated_state)
                assert len(posts)==1
                entry.update(delivery='PASS',**observed,completed_at=pulse.now())
            except Exception as exc:
                entry.update(delivery='FAIL_OR_UNCERTAIN',error_type=type(exc).__name__)
            finally:
                pulse.STATE=original_state;pulse.request=original_request
        save(d);persist()

def diagnose(d):
    cfg=pulse.load(ROOT/'config.json',{})
    term=cfg['search_keywords'][0]
    args={'key':pulse.KEY,'visitor_id':pulse.VISITOR,'store_id':cfg['target_store_id'],'pricing_store_id':cfg['target_store_id'],'zip':cfg['target_zip'],'channel':'WEB','keyword':term,'count':24,'offset':0,'default_purchasability_filter':'false','page':'/search','platform':'desktop'}
    urls={'target':pulse.BASE+'plp_search_v2?'+urllib.parse.urlencode(args),'walmart':'https://www.walmart.com/search?'+urllib.parse.urlencode({'q':term,'page':1})}
    d.setdefault('hosted',{})
    for retailer,url in urls.items():
        if retailer in d['hosted']:
            print(retailer+': existing diagnostic retained; no retry');continue
        entry={'checked_at':pulse.now(),'requests':1,'result':'FAIL','endpoint':urllib.parse.urlsplit(url).netloc+urllib.parse.urlsplit(url).path,'user_agent':'PHASE-PULSE-Beta/0.1','cookies':False,'retry':False}
        req=urllib.request.Request(url,headers={'User-Agent':'PHASE-PULSE-Beta/0.1','Accept':'application/json,text/html'})
        try:
            try: r=urllib.request.build_opener(pulse.NoRedirect).open(req,timeout=25)
            except urllib.error.HTTPError as error:r=error
            with r:
                body=r.read(5_000_001);entry['http_status']=r.code
                entry['content_type']=r.headers.get('Content-Type','')
                entry['server']=r.headers.get('Server','')
            text=body.decode('utf-8',errors='replace')
            title=re.search(r'<title[^>]*>(.*?)</title>',text,re.S|re.I)
            if title:entry['page_title']=re.sub('<[^>]+>','',title[1])[:180]
            entry['response_bytes']=len(body)
            entry['challenge_signals']=[s for s in ['verify you are human','robot or human','access denied','px-captcha','captcha','request rejected','request blocked','automated'] if s in text.lower()]
            if r.code==200 and not entry['challenge_signals']:
                if retailer=='walmart':
                    products,count=pulse.walmart_parse(text,cfg)
                    known=[p for p in products if p['status']!='unknown']
                    entry.update(result='PASS' if known else 'FAIL',products_checked=len(known),records_retrieved=count)
                else:
                    parsed=json.loads(text)
                    entry['search_records']=len(parsed.get('data',{}).get('search',{}).get('products',[]))
                    entry['note']='Search response alone is insufficient: per-product fulfillment still requires verification.'
            else:entry['note']='Request stopped. No alternate endpoint or automatic retry.'
        except Exception as exc:entry['error_type']=type(exc).__name__
        d['hosted'][retailer]=entry;save(d);persist()

def main():
    before={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['state.json','report.json']}
    d=pulse.load(LEDGER,{'run_id':os.environ.get('PULSE_RUN_ID'),'created_at':pulse.now()})
    tests(d);diagnose(d)
    after={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in before}
    assert before==after,'Production baseline changed unexpectedly'
    d['baseline_preserved']=True;d['completed_at']=pulse.now();save(d);persist()
    summary=json.dumps(d,indent=2)
    print(summary)
    with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as f:f.write('## Isolated PHASE verification\n\n```json\n'+summary+'\n```\n')
    return 0 if all(x.get('delivery')=='PASS' for x in d['tests'].values()) else 1
if __name__=='__main__':sys.exit(main())
