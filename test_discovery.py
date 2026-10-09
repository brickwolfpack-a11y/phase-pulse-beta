import copy,json,pathlib,tempfile,unittest
from unittest.mock import patch
import discovery,pulse
CFG={'include_keywords':['pokemon','one piece','topps','panini','funko'],'search_keywords':['pokemon','one piece'],'search_pages':1,'target_discovery_request_budget':2,'max_target_products':2,'target_tcins':['95120834']}
def raw(tcin='95120834',seller=False,name='Pokémon Trading Cards'):
 return {'tcin':tcin,'item':{'product_description':{'title':name},'enrichment':{'buy_url':'https://www.target.com/p/cards/-/A-'+tcin},'fulfillment':{'is_marketplace':seller},'product_classification':{'item_type':{'name':'Collectible Trading Cards'}}}}
def page(rows):return {'data':{'search':{'products':rows}}}
class DiscoveryTests(unittest.TestCase):
 def test_identity_filters_and_stock_separation(self):
  p=discovery.normalize(raw(),CFG,'one');self.assertEqual(p['inventory_status'],'unknown');self.assertTrue(p['eligible_for_inventory'])
  self.assertIsNone(discovery.normalize(raw(name='Ordinary towel'),CFG,'one'))
  r=raw();r['item']['enrichment']['buy_url']='https://target.com.evil/p/-/A-95120834';self.assertIsNone(discovery.normalize(r,CFG,'one'))
  r=raw();r['item']['enrichment']['buy_url']='https://www.target.com/p/-/A-95120835';self.assertIsNone(discovery.normalize(r,CFG,'one'))
 def test_marketplace_and_unknown_seller_never_eligible(self):
  for seller in [True,None]:self.assertFalse(discovery.normalize(raw(seller=seller),CFG,'one')['eligible_for_inventory'])
 def test_category_and_exclusion_filters(self):
  cfg={**CFG,'exclude_keywords':['towel'],'target_discovery_categories':['trading cards']}
  self.assertIsNone(discovery.normalize(raw(name='Pokemon towel'),cfg,'one'))
  r=raw();r['item']['product_classification']['item_type']['name']='Shirts';self.assertIsNone(discovery.normalize(r,cfg,'one'))
 def test_new_listing_once_baseline_and_new_scope_silent(self):
  d={};p=discovery.normalize(raw(),CFG,'one')
  self.assertFalse(discovery.absorb(d,[p],'pokemon:0','one'))
  q=discovery.normalize(raw('95120835'),CFG,'two')
  self.assertEqual(len(discovery.absorb(d,[p,q],'pokemon:0','two')),1)
  restored=json.loads(json.dumps(d));self.assertFalse(discovery.absorb(restored,[p,q],'pokemon:0','three'))
  self.assertFalse(discovery.absorb(restored,[discovery.normalize(raw('95120836'),CFG,'three')],'new-keyword:0','three'))
  self.assertEqual(restored['products']['95120834']['first_seen'],'one')
 def test_missing_listing_does_not_refresh_or_delete(self):
  d={};p=discovery.normalize(raw(),CFG,'one');discovery.absorb(d,[p],'a','one');discovery.absorb(d,[],'a','two')
  self.assertEqual(d['products'][p['id']]['last_seen'],'one')
 def test_partial_failure_preserves_discovery_but_no_stock(self):
  old={'products':{'95120834':{'status':'out_of_stock','checked_at':'old'}}}
  fetch=unittest.mock.Mock(side_effect=[page([raw()]),pulse.CheckError('HTTP 435',True)])
  with self.assertRaises(pulse.CheckError):discovery.collect(CFG,old,fetch,lambda:'now',lambda _:None)
  self.assertEqual(fetch.call_count,2);self.assertIn('95120834',old['discovery']['products']);self.assertEqual(old['products']['95120834']['checked_at'],'old')
 def test_budget_and_page_rotation(self):
  cfg={**CFG,'search_pages':2,'target_discovery_request_budget':1};old={};seen=[]
  def fetch(endpoint,args,cfg):seen.append((args['keyword'],args['offset']));return page([])
  for _ in range(4):discovery.collect(cfg,old,fetch,lambda:'now',lambda _:None)
  self.assertEqual(seen,[('pokemon',0),('pokemon',24),('one piece',0),('one piece',24)])
 def test_watchlist_auto_tracking_and_fair_rotation(self):
  old={'discovery':{'products':{str(i):discovery.normalize(raw(str(i)),CFG,'now') for i in range(95120834,95120839)}}}
  first=discovery.select_watchlist(CFG,old);second=discovery.select_watchlist(CFG,old)
  self.assertEqual(first,['95120834','95120835']);self.assertEqual(second,['95120836','95120837'])
 def test_collector_uses_shipping_not_search_stock(self):
  cfg={**CFG,'target_discovery_request_budget':1,'request_spacing_seconds':0}
  old={'products':{}}
  responses=[page([raw()]),{'data':{'product':{'tcin':'95120834','fulfillment':{'shipping_options':{'availability_status':'OUT_OF_STOCK'}}}}}]
  with patch.object(pulse,'target_get',side_effect=responses) as get,patch.object(pulse.time,'sleep'):
   rows,_=pulse.check_target(cfg,old)
   self.assertEqual(rows[0]['status'],'out_of_stock');self.assertEqual(get.call_args_list[1].args[0],'product_fulfillment_and_variation_hierarchy_v1')
 def test_paused_sources_make_zero_requests(self):
  cfg={**CFG,'paused_retailers':{'target':'CAPTCHA','walmart':'CAPTCHA'}}
  with tempfile.TemporaryDirectory() as tmp,patch.object(pulse,'STATE',pathlib.Path(tmp)/'s.json'),patch.object(pulse,'REPORT',pathlib.Path(tmp)/'r.json'),patch.object(pulse,'request') as req:
   self.assertEqual(pulse.check(cfg,{}),1);req.assert_not_called()
if __name__=='__main__':unittest.main()
