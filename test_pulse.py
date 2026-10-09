import sys,pathlib,unittest,json,tempfile,os
from unittest.mock import patch
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import pulse
class Tests(unittest.TestCase):
 def test_target_explicit_stock(self):
  self.assertEqual(pulse.target_status({}),'unknown')
  self.assertEqual(pulse.target_status({'shipping_options':{'availability_status':'OUT_OF_STOCK'}}),'out_of_stock')
  self.assertEqual(pulse.target_status({'shipping_options':{'availability_status':'PRE_ORDER_SELLABLE'}}),'pre_order')
 def test_walmart_no_guess(self):
  self.assertEqual(pulse.walmart_status({'canAddToCart':True}),'unknown')
  self.assertEqual(pulse.walmart_status({'availabilityStatusV2':{'value':'IN_STOCK'},'isOutOfStock':True}),'out_of_stock')
 def test_baseline_and_dedup(self):
  old={};p={'id':'1','status':'out_of_stock','checked_at':'2026-10-09T00:00:00+00:00'}
  self.assertEqual(pulse.merge(old,[p],'target'),[])
  q={**p,'status':'in_stock','checked_at':'2026-10-09T00:15:00+00:00'}
  self.assertEqual(len(pulse.merge(old,[q],'target')),1)
  self.assertEqual(pulse.merge(old,[q],'target'),[])
 def test_missing_not_oos(self):
  old={'products':{'1':{'id':'1','status':'in_stock','checked_at':'x'}}}
  pulse.merge(old,[],'target');pulse.merge(old,[{'id':'1','status':'unknown'}],'target')
  self.assertEqual(old['products']['1']['status'],'in_stock')
  self.assertEqual(old['products']['1']['checked_at'],'x')
 def test_new_stock_silent(self):
  self.assertEqual(pulse.merge({},[{'id':'1','status':'in_stock','checked_at':'x'}],'walmart'),[])
 def test_url_validation(self):
  self.assertFalse(pulse.valid_url('https://walmart.com.evil.example/ip/1','walmart'))
  self.assertFalse(pulse.valid_url('https://evil@walmart.com/ip/1','walmart'))
  self.assertTrue(pulse.valid_url('https://www.walmart.com/ip/1','walmart'))
 def test_seller_and_keyword(self):
  items=[{'usItemId':'1','name':'Pokémon cards','sellerName':'Walmart.com','canonicalUrl':'/ip/1','availabilityStatusV2':{'value':'IN_STOCK'}},{'usItemId':'2','name':'Pokemon cards','sellerName':'Other','canonicalUrl':'/ip/2'},{'usItemId':'3','name':'Board game','sellerName':'Walmart.com','canonicalUrl':'/ip/3'}]
  data={'props':{'pageProps':{'initialData':{'searchResult':{'itemStacks':[{'items':items}]}}}}}
  rows,count=pulse.walmart_parse('<script id="__NEXT_DATA__">'+json.dumps(data)+'</script>',{'include_keywords':['pokemon']})
  self.assertEqual(len(rows),1);self.assertEqual(count,3)
 def test_schema_error_not_empty_success(self):
  with self.assertRaises(pulse.CheckError):pulse.walmart_parse('<html>No stock data</html>',{})
class FailureTests(unittest.TestCase):
 def test_failed_check_preserves_baseline_and_pauses(self):
  state={'target':{'products':{'1':{'status':'out_of_stock'}},'last_success':'old'},'walmart':{'paused':'blocked','products':{}}}
  with tempfile.TemporaryDirectory() as tmp, patch.object(pulse,'STATE',pathlib.Path(tmp)/'state.json'), patch.object(pulse,'REPORT',pathlib.Path(tmp)/'report.json'), patch.object(pulse,'check_target',side_effect=pulse.CheckError('HTTP 403',True)):
   self.assertEqual(pulse.check({},state),1)
   self.assertEqual(state['target']['products']['1']['status'],'out_of_stock')
   self.assertEqual(state['target']['last_success'],'old')
   self.assertEqual(state['target']['paused'],'HTTP 403')
 def test_old_reservation_not_replayed(self):
  state={'outbox':[{'delivery':'reserved','reservation':'old'}]}
  with tempfile.TemporaryDirectory() as tmp, patch.object(pulse,'STATE',pathlib.Path(tmp)/'state.json'), patch.dict(os.environ,{'PULSE_RUN_ID':'new'}), patch.object(pulse,'request') as req:
   pulse.deliver({'max_alerts_per_run':10},state);req.assert_not_called()
if __name__=='__main__':unittest.main()
