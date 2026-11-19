"""Read-only authenticated report viewer. Does not connect to Stockbit."""
import html,json,os,secrets
from pathlib import Path
from fastapi import Depends,FastAPI,HTTPException
from fastapi.responses import HTMLResponse,Response
from fastapi.security import HTTPBasic,HTTPBasicCredentials
from .delivery import configured_store,read_latest

app=FastAPI(docs_url=None,redoc_url=None,openapi_url=None)
security=HTTPBasic()

def authorize(credentials:HTTPBasicCredentials=Depends(security)):
    user=os.getenv('ROWLET_VIEW_USER','')
    password=os.getenv('ROWLET_VIEW_PASSWORD','')
    if not user or len(password)<16:raise HTTPException(503,'Viewer credentials not configured')
    user_ok=secrets.compare_digest(credentials.username.encode(),user.encode())
    pass_ok=secrets.compare_digest(credentials.password.encode(),password.encode())
    if not (user_ok and pass_ok):raise HTTPException(401,'Authentication required',headers={'WWW-Authenticate':'Basic'})

def store():
    root=os.getenv('ROWLET_REPORT_DIR')
    if not root and not os.getenv('ROWLET_S3_BUCKET'):raise HTTPException(503,'Report storage not configured')
    return configured_store(Path(root or '.'))

@app.get('/',response_class=HTMLResponse,dependencies=[Depends(authorize)])
def home():
    try:
        source=store()
        manifest=json.loads(source.get('latest.json'))
        session=html.escape(str(manifest['session']))
        published=html.escape(str(manifest['published_at']))
    except HTTPException:raise
    except Exception:raise HTTPException(503,'Belum ada laporan yang dapat dibaca') from None
    try:
        status=json.loads(source.get('status.json'))
        state=html.escape(str(status.get('state','unknown')))
        attempted=html.escape(str(status.get('attempted_at','-')))
    except Exception:state='Tidak tersedia';attempted='-'
    return HTMLResponse(f'''<!doctype html><html lang="id"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>RowletAI Reports</title>
<style>body{{font:16px system-ui;background:#eef4f6;color:#193d49;margin:0;padding:8vw}}main{{max-width:720px;background:white;border-top:6px solid #078776;padding:36px;border-radius:12px;margin:auto}}a{{display:inline-block;background:#087e70;color:white;padding:14px 22px;border-radius:8px;text-decoration:none}}small{{color:#526870}}footer{{margin-top:32px;font-size:12px}}</style>
<main><small>ROWLETAI · IDX OBSERVATORY</small><h1>Laporan pasar harian</h1>
<h2>Sesi {session}</h2><p>Terbit (UTC): {published}</p>
<p>Status pembaruan: <strong>{state}</strong><br><small>Pemeriksaan: {attempted}</small></p>
<p>Tanggal sesi di atas adalah tanggal data PDF terakhir yang berhasil diterbitkan.</p>
<a href="/report.pdf">Unduh PDF</a><footer>Created by RowletAI. Not a Recommendation to Buy or Sell. Just for research only.</footer></main></html>''',headers={'Cache-Control':'no-store'})

@app.get('/report.pdf',dependencies=[Depends(authorize)])
def report_pdf():
    try:manifest,pdf=read_latest(store())
    except HTTPException:raise
    except Exception:raise HTTPException(503,'Laporan belum tersedia atau gagal diverifikasi') from None
    return Response(pdf,media_type='application/pdf',headers={'Content-Disposition':'attachment; filename="RowletAI-report.pdf"','Cache-Control':'no-store'})
