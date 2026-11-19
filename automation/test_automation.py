import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from automation.delivery import LocalStore,publish,read_latest
from automation.run_daily import validate,finite

class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=LocalStore(self.temp.name)
    def test_roundtrip(self):
        manifest=publish(self.store,'2026-10-22',b'%PDF-test',{'session':'2026-10-22'})
        actual,pdf=read_latest(self.store)
        self.assertEqual(actual,manifest);self.assertEqual(pdf,b'%PDF-test')
    def test_failure_preserves_previous_latest(self):
        old=publish(self.store,'2026-10-21',b'%PDF-old',{})
        original=self.store.put
        def failing(key,*args):
            if key.endswith('summary.json'):raise OSError('delivery failed')
            return original(key,*args)
        with patch.object(self.store,'put',side_effect=failing):
            with self.assertRaises(OSError):publish(self.store,'2026-10-22',b'%PDF-new',{})
        self.assertEqual(read_latest(self.store)[0],old)
    def test_corrupt_pdf_rejected(self):
        manifest=publish(self.store,'2026-10-22',b'%PDF-test',{})
        self.store.put(manifest['pdf'],b'corrupt','application/pdf')
        with self.assertRaises(ValueError):read_latest(self.store)
    def test_unsafe_path_rejected(self):
        self.store.put('latest.json',json.dumps({'pdf':'../secret'}).encode(),'application/json')
        with self.assertRaises(ValueError):read_latest(self.store)
    def test_freshness_and_coverage(self):
        report={'session':'2026-10-22','index':{'as_of':'2026-10-22'},'requested':100,'aligned':80,'buy_signals':[]}
        with patch.dict(os.environ,{'ROWLET_MIN_COVERAGE':'0.75'}):
            validate(report,'2026-10-22')
            for changes in [{'session':'2026-10-21'},{'index':{}},{'aligned':74},{'requested':0},{'buy_signals':[{'buy_signal':{'signal_date':'2026-10-21','age':1}}]}]:
                with self.subTest(changes=changes),self.assertRaises(ValueError):validate(dict(report,**changes),'2026-10-22')
    def test_finite(self):self.assertEqual(finite({'x':[float('nan'),float('inf'),2]}),{'x':[None,None,2]})
    def test_viewer_requires_auth_and_serves_pdf(self):
        from fastapi.testclient import TestClient
        from automation.viewer import app
        publish(self.store,'2026-10-22',b'%PDF-test',{})
        with patch.dict(os.environ,{'ROWLET_VIEW_USER':'research','ROWLET_VIEW_PASSWORD':'test-password-123456','ROWLET_REPORT_DIR':self.temp.name,'ROWLET_S3_BUCKET':''}):
            client=TestClient(app)
            self.assertEqual(client.get('/').status_code,401)
            self.assertEqual(client.get('/',auth=('research','wrong')).status_code,401)
            response=client.get('/',auth=('research','test-password-123456'))
            self.assertEqual(response.status_code,200);self.assertIn('2026-10-22',response.text)
            self.assertEqual(client.get('/report.pdf',auth=('research','test-password-123456')).content,b'%PDF-test')
            with patch.dict(os.environ,{'ROWLET_VIEW_PASSWORD':''}):
                self.assertEqual(client.get('/',auth=('research','anything')).status_code,503)

if __name__=='__main__':unittest.main()
