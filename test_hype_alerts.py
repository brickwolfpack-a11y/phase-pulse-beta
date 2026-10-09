import copy,json,pathlib,tempfile,unittest
from unittest.mock import patch
import discovery,pulse
from test_discovery import CFG,raw

class HypeAlerts(unittest.TestCase):
 def product(self,tcin='95120834'):
  r=raw(tcin);r['price']={'formatted_current_price':'$29.99'}
  r['item']['enrichment']['images']={'primary_image_url':'https://target.scene7.com/is/image/Target/GUEST-example'}
  return discovery.normalize(r,CFG,pulse.now())
 def state_with_event(self):
  d={};a=self.product();b=self.product('95120835')
  discovery.absorb(d,[a],'same',pulse.now())
  discovery.absorb(d,[a,b],'same',pulse.now())
  return {'target':{'discovery':d}}
 def test_metadata_and_safe_image(self):
  p=self.product();self.assertEqual(p['price'],'$29.99');self.assertIn('target.scene7.com',p['image'])
  r=raw();r['item']['enrichment']['images']={'primary_image_url':'https://evil.test/a'}
  self.assertIsNone(discovery.normalize(r,CFG,pulse.now())['image'])
 def test_journal_outbox_persisted_duplicate_suppression(self):
  s=self.state_with_event();self.assertEqual(pulse.queue_discoveries(s),1)
  restored=json.loads(json.dumps(s));self.assertEqual(pulse.queue_discoveries(restored),0)
  self.assertEqual(len(restored['outbox']),1)
  e=restored['outbox'][0];self.assertEqual(e['product']['status'],'unknown')
  payload=pulse.alert_payload(e);embed=payload['embeds'][0]
  self.assertTrue(embed['title'].startswith('NEW TO MONITOR'))
  self.assertIn('unverified',embed['description']);self.assertIn('thumbnail',embed)
  self.assertEqual(payload['allowed_mentions'],{'parse':[]})
 def test_legacy_journal_is_not_replayed(self):
  s=self.state_with_event();s['target']['discovery']['events'][0].pop('notification_version')
  self.assertEqual(pulse.queue_discoveries(s),0)
 def test_preorder_opens_once_then_restock_once(self):
  p={**self.product(),'status':'out_of_stock','checked_at':pulse.now(),'evidence':'fixture'};old={}
  self.assertEqual(pulse.merge(old,[p],'target'),[])
  p={**p,'status':'pre_order'};events=pulse.merge(old,[p],'target')
  self.assertEqual(events[0]['kind'],'preorder_open');self.assertEqual(pulse.merge(old,[p],'target'),[])
  self.assertTrue(pulse.alert_payload(events[0])['embeds'][0]['title'].startswith('PREORDER OPEN'))
  p={**p,'status':'in_stock'};self.assertEqual(pulse.merge(old,[p],'target')[0]['kind'],'restock')
  self.assertEqual(pulse.merge(old,[p],'target'),[])
 def test_new_inventory_baseline_unknown_never_alerts(self):
  old={};p={**self.product(),'status':'pre_order','checked_at':pulse.now()}
  self.assertEqual(pulse.merge(old,[p],'target'),[])
  self.assertEqual(pulse.merge(old,[{**p,'status':'unknown'}],'target'),[])
  self.assertEqual(old['products'][p['id']]['status'],'pre_order')
 def test_check_queues_discovery_even_inventory_fails(self):
  s={}
  def collector(cfg,old):
   old.update(self.state_with_event()['target']);raise pulse.CheckError('HTTP 435',True)
  with tempfile.TemporaryDirectory() as tmp,patch.object(pulse,'STATE',pathlib.Path(tmp)/'s.json'),patch.object(pulse,'REPORT',pathlib.Path(tmp)/'r.json'),patch.object(pulse,'check_target',collector):
   pulse.check({'paused_retailers':{'walmart':'paused'}},s)
   saved=json.loads((pathlib.Path(tmp)/'s.json').read_text());self.assertEqual(len(saved['outbox']),1)
   self.assertEqual(saved['target']['paused'],'HTTP 435')
 def test_discovery_delivery_uses_existing_reservation(self):
  s=self.state_with_event();pulse.queue_discoveries(s)
  e=s['outbox'][0];e.update(delivery='reserved',reservation='test-local')
  with tempfile.TemporaryDirectory() as tmp,patch.object(pulse,'STATE',pathlib.Path(tmp)/'s.json'),patch.dict(pulse.os.environ,{'PULSE_RUN_ID':'test-local'}),patch.object(pulse,'webhook',return_value='https://example.invalid/test'),patch.object(pulse,'request',return_value='{"id":"fixture"}') as request,patch.object(pulse.time,'sleep'):
   pulse.deliver({'max_alerts_per_run':10},s);pulse.deliver({'max_alerts_per_run':10},s)
   self.assertEqual(request.call_count,1);self.assertEqual(e['delivery'],'sent')
   self.assertIn('NEW TO MONITOR',request.call_args.args[1]['embeds'][0]['title'])

if __name__=='__main__':unittest.main()
