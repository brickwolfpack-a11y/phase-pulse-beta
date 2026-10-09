"""Offline regression tests; never contact Target or Discord."""
import copy,json,pathlib,tempfile,unittest
from unittest.mock import patch
import pulse

ROOT=pathlib.Path(__file__).resolve().parent
class TargetCollectorTests(unittest.TestCase):
 def setUp(self):
  self.cfg={'target_tcins':['95120834'],'search_keywords':['pokemon'],'include_keywords':['pokemon'],'max_target_products':1,'target_discovery_request_budget':1}
  self.old={'products':{'95120834':{'id':'95120834','name':'Pokemon cards','url':'https://www.target.com/p/cards/-/A-95120834','status':'out_of_stock','checked_at':'2026-10-09T01:15:10+00:00'}}}
  self.stock={'data':{'product':{'tcin':'95120834','fulfillment':{'shipping_options':{'availability_status':'OUT_OF_STOCK'}}}}}
 def test_search_failure_keeps_known_watchlist(self):
  for error in [pulse.CheckError('Network request failed'),ValueError('Search schema changed')]:
   old=copy.deepcopy(self.old)
   with patch('discovery.collect',side_effect=error),patch.object(pulse,'target_get',return_value=self.stock) as get,patch.object(pulse.time,'sleep'):
    rows,count=pulse.check_target(self.cfg,old)
   self.assertEqual(count,1);self.assertEqual(rows[0]['status'],'out_of_stock');get.assert_called_once()
   self.assertEqual(old['discovery']['last_run']['status'],'error')
 def test_access_challenge_never_falls_back_to_stock_request(self):
  with patch('discovery.collect',side_effect=pulse.CheckError('HTTP 435',True)),patch.object(pulse,'target_get') as get:
   with self.assertRaises(pulse.CheckError):pulse.check_target(self.cfg,self.old)
   get.assert_not_called()
 def test_null_and_unrecognized_shipping_stays_unknown(self):
  for value in [None,{}, {'shipping_options':None},{'shipping_options':[]},{'shipping_options':{'availability_status':'NEW_STATUS'}}]:
   self.assertEqual(pulse.target_status(value),'unknown')
 def test_malformed_product_is_retrieval_error(self):
  for response in [None,{}, {'data':None},{'data':{'product':None}}]:
   with patch('discovery.collect'),patch.object(pulse,'target_get',return_value=response):
    with self.assertRaises(pulse.CheckError):pulse.check_target(self.cfg,self.old)
 def test_identity_mismatch_is_not_inventory(self):
  self.stock['data']['product']['tcin']='95120835'
  with patch('discovery.collect'),patch.object(pulse,'target_get',return_value=self.stock):
   with self.assertRaises(pulse.CheckError):pulse.check_target(self.cfg,self.old)
 def test_degraded_discovery_report_and_persistent_unchanged_stock(self):
  cfg={**self.cfg,'paused_retailers':{'walmart':'Existing pause'}}
  with tempfile.TemporaryDirectory() as tmp,patch.object(pulse,'STATE',pathlib.Path(tmp)/'state.json'),patch.object(pulse,'REPORT',pathlib.Path(tmp)/'report.json'),patch('discovery.collect',side_effect=ValueError('Search schema changed')),patch.object(pulse,'target_get',return_value=self.stock),patch.object(pulse.time,'sleep'):
   state={'target':copy.deepcopy(self.old),'outbox':[]}
   for _ in range(2):
    self.assertEqual(pulse.check(cfg,state),1)
    state=json.loads(pulse.STATE.read_text())
    report=json.loads(pulse.REPORT.read_text())
    self.assertEqual(report['retailers']['target']['status'],'partial')
    self.assertEqual(report['retailers']['target']['products_checked'],1)
    self.assertEqual(state['outbox'],[])
 def test_saved_genuine_hosted_evidence_separates_success_and_block(self):
  checks=json.loads((ROOT/'verification.json').read_text())['direct_shipping_checks']
  self.assertEqual(checks[0]['products'][0]['id'],'95120834')
  self.assertEqual(checks[0]['products'][0]['source_status'],'OUT_OF_STOCK')
  self.assertEqual(checks[1]['http_status'],435)
  self.assertIn('captcha',checks[1]['challenge_signals'])
if __name__=='__main__':unittest.main()
