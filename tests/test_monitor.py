import copy
import json
import unittest
from unittest.mock import patch
from eirewatch.core import Monitor
from eirewatch.collectors import collect,check_url
from eirewatch.report import render

NOW='2026-10-10T10:00:00+00:00'
CONFIG={'id':'test','url':'https://example.org/feed','allowed_hosts':['example.org'],'adapter':'normalized-json-v1','max_age_hours':2,'approved_for_ingestion':True,'official':True}
RECORD={'id':'one','title':'Test closure','category':'road','areas':['Cork'],'issued':'2026-10-10T08:00:00+00:00','updated':'2026-10-10T09:00:00+00:00','expires':'2026-10-10T18:00:00+00:00','status':'active','url':'https://example.org/one','instruction':'Test only'}

class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.m=Monitor(':memory:');self.m.register(CONFIG);self.m.subscribe('cork',['Cork'],['road'])
    def tearDown(self):self.m.db.close()
    def load(self,r=None):
        self.m.ingest('test',[r or RECORD],NOW)
        return self.m.snapshot(NOW)['incidents'][0]['id']
    def approve(self,id,revision=1):self.m.review(id,revision,'approved','reviewer',NOW)
    def test_idempotent_ingestion_and_outbox(self):
        id=self.load();self.assertEqual(self.m.ingest('test',[RECORD],NOW),0)
        self.assertEqual(self.m.queue(NOW),0);self.approve(id)
        self.assertEqual(self.m.queue(NOW),1);self.assertEqual(self.m.queue(NOW),0)
        self.assertEqual(len(self.m.snapshot(NOW)['history']),1)
    def test_update_invalidates_approval_and_old_notification(self):
        id=self.load();self.approve(id);self.m.queue(NOW)
        r={**RECORD,'instruction':'Updated instructions','updated':NOW};self.load(r)
        self.assertEqual(self.m.inbox('cork',NOW),[])
        with self.assertRaises(ValueError):self.approve(id)
        self.approve(id,2);self.assertEqual(self.m.queue(NOW),1)
        self.assertEqual(self.m.inbox('cork',NOW)[0]['revision'],2)
    def test_resolution_to_existing_subscriber(self):
        id=self.load();self.approve(id);self.m.queue(NOW)
        self.load({**RECORD,'status':'resolved','updated':NOW});self.approve(id,2)
        self.assertEqual(self.m.queue(NOW),1)
        self.assertEqual(self.m.inbox('cork',NOW)[0]['data']['status'],'resolved')
    def test_empty_feed_not_resolution(self):
        self.load();self.m.ingest('test',[],NOW)
        self.assertEqual(self.m.snapshot(NOW)['incidents'][0]['data']['status'],'active')
    def test_expired_future_and_no_expiry_do_not_alert(self):
        for changes in ({'expires':'2026-10-10T09:30:00Z'},{'issued':'2026-10-10T11:00:00Z','updated':'2026-10-10T11:00:00Z'},{'expires':None}):
            m=Monitor(':memory:');m.register(CONFIG);m.subscribe('cork',[],[])
            m.ingest('test',[{**RECORD,**changes}],NOW);row=m.snapshot(NOW)['incidents'][0];m.review(row['id'],1,'approved','tester',NOW)
            self.assertEqual(m.queue(NOW),0);m.db.close()
    def test_health_failure_and_stale_suppresses_inbox(self):
        id=self.load();self.approve(id);self.m.queue(NOW)
        self.assertEqual(self.m.health('2026-10-10T13:00:00Z')[0]['status'],'stale')
        self.assertEqual(self.m.inbox('cork','2026-10-10T13:00:00Z'),[])
        self.m.failure('test','error',NOW);self.assertEqual(self.m.queue(NOW),0)
        self.assertEqual(self.m.health(NOW)[0]['status'],'unavailable')
    def test_atomic_validation(self):
        with self.assertRaises(ValueError):self.m.ingest('test',[RECORD,{**RECORD,'id':'bad','issued':'invalid'}],NOW)
        self.assertEqual(self.m.snapshot(NOW)['incidents'],[])
    def test_disabled_and_unofficial(self):
        self.m.register({**CONFIG,'approved_for_ingestion':False})
        with self.assertRaises(ValueError):self.load()
        self.m.register({**CONFIG,'official':False});id=self.load();self.approve(id)
        self.assertEqual(self.m.queue(NOW),0)
    def test_ack_ownership_and_opt_out(self):
        id=self.load();self.approve(id);self.m.queue(NOW);notification=self.m.inbox('cork',NOW)[0]['id']
        with self.assertRaises(ValueError):self.m.acknowledge(notification,'other',NOW)
        self.m.acknowledge(notification,'cork',NOW);self.assertEqual(self.m.inbox('cork',NOW),[])
        self.m.subscribe('cork',[],[],False);self.assertEqual(self.m.queue(NOW),0)
    def test_retry_backoff_and_recovery(self):
        fail=lambda c:(_ for _ in ()).throw(ValueError('secret body'))
        self.assertEqual(collect(self.m,CONFIG,NOW,fail),'unavailable')
        self.assertEqual(collect(self.m,CONFIG,NOW,fail),'backoff')
        good=lambda c:({'schema_version':1,'incidents':[RECORD]},'hash')
        self.assertEqual(collect(self.m,CONFIG,'2026-10-10T10:03:00Z',good),'healthy')
        self.assertIsNone(self.m.health(NOW)[0]['error'])
    def test_private_targets_rejected(self):
        with self.assertRaises(ValueError):check_url('http://example.org', ['example.org'])
        with self.assertRaises(ValueError):check_url('https://other.org', ['example.org'])
        with patch('socket.getaddrinfo',return_value=[(None,None,None,None,('127.0.0.1',443))]):
            with self.assertRaises(ValueError):check_url('https://example.org',['example.org'])
    def test_html_escaping(self):
        self.load({**RECORD,'title':'<script>alert(1)</script>'})
        report=render(self.m.snapshot(NOW));self.assertNotIn('<script>alert(1)</script>',report)
        self.assertIn('&lt;script&gt;',report)
    def test_old_revision_ignored(self):
        self.load();self.load({**RECORD,'updated':'2026-10-10T08:30:00Z','title':'Older'})
        self.assertEqual(self.m.snapshot(NOW)['incidents'][0]['revision'],1)
    def test_area_category_filter(self):
        self.m.subscribe('dublin',['Dublin'],['road']);id=self.load();self.approve(id)
        self.assertEqual(self.m.queue(NOW),1);self.assertEqual(self.m.inbox('dublin',NOW),[])

if __name__=='__main__':unittest.main()
