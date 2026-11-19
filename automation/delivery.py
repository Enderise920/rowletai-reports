"""Publish immutable report bundles; switch latest only after all files succeed."""
import hashlib,json,os,re,uuid
from pathlib import Path
from datetime import datetime,timezone

class LocalStore:
    def __init__(self,root):self.root=Path(root)
    def put(self,key,body,content_type):
        path=self.root/key;path.parent.mkdir(parents=True,exist_ok=True)
        tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
        try:tmp.write_bytes(body);os.replace(tmp,path)
        finally:tmp.unlink(missing_ok=True)
    def get(self,key):return (self.root/key).read_bytes()

class S3Store:
    def __init__(self):
        import boto3
        from botocore.config import Config
        self.client=boto3.client('s3',endpoint_url=os.getenv('ROWLET_S3_ENDPOINT') or None,config=Config(connect_timeout=10,read_timeout=30,retries={'max_attempts':2}))
        self.bucket=os.environ['ROWLET_S3_BUCKET'];self.prefix=os.getenv('ROWLET_S3_PREFIX','rowlet').strip('/')
    def key(self,key):return self.prefix+'/'+key if self.prefix else key
    def put(self,key,body,content_type):self.client.put_object(Bucket=self.bucket,Key=self.key(key),Body=body,ContentType=content_type)
    def get(self,key):return self.client.get_object(Bucket=self.bucket,Key=self.key(key))['Body'].read()

def configured_store(root):
    return S3Store() if os.getenv('ROWLET_S3_BUCKET') else LocalStore(root)

def publish(store,session,pdf,summary):
    from datetime import date
    date.fromisoformat(session)
    if not pdf.startswith(b'%PDF-'):raise ValueError('Invalid PDF')
    # A retry never overwrites objects referenced by the last successful manifest.
    prefix=f'reports/{session}/{uuid.uuid4().hex}'
    manifest={'schema':1,'session':session,'published_at':datetime.now(timezone.utc).isoformat(),'pdf':prefix+'/report.pdf','summary':prefix+'/summary.json','sha256':hashlib.sha256(pdf).hexdigest()}
    store.put(manifest['pdf'],pdf,'application/pdf')
    store.put(manifest['summary'],json.dumps(summary,allow_nan=False).encode(),'application/json')
    store.put('latest.json',json.dumps(manifest).encode(),'application/json')
    return manifest

def read_latest(store):
    manifest=json.loads(store.get('latest.json'))
    key=manifest['pdf']
    if not re.fullmatch(r'reports/\d{4}-\d{2}-\d{2}/[a-f0-9]{32}/report\.pdf',key):raise ValueError('Invalid report key')
    pdf=store.get(key)
    if hashlib.sha256(pdf).hexdigest()!=manifest['sha256']:raise ValueError('Report checksum mismatch')
    return manifest,pdf
