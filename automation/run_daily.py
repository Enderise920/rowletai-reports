"""Scheduled runner for the existing persistent Windows installation. No Telegram sends."""
import argparse,importlib.util,json,math,os,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor,as_completed
try:
    from .delivery import configured_store,publish
except ImportError:
    from delivery import configured_store,publish

def finite(x):
    if isinstance(x,float) and not math.isfinite(x):return None
    if isinstance(x,dict):return {k:finite(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [finite(v) for v in x]
    return x

def validate(report,session):
    if report.get('session')!=session:raise ValueError('session_not_ready')
    if not report.get('index') or 'error' in report['index'] or report['index'].get('as_of')!=session:raise ValueError('index_not_ready')
    minimum=float(os.getenv('ROWLET_MIN_COVERAGE','0.75'))
    if not 0<minimum<=1:raise ValueError('invalid_coverage_threshold')
    if report.get('requested',0)<=0 or report.get('aligned',0)<report['requested']*minimum:raise ValueError('coverage_not_ready')
    for row in report.get('buy_signals',[]):
        if row['buy_signal'].get('signal_date')!=session or row['buy_signal'].get('age')!=0:raise ValueError('signal_date_mismatch')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--app-dir',required=True);parser.add_argument('--check',action='store_true');args=parser.parse_args()
    root=Path(args.app_dir).resolve();sys.path.insert(0,str(root));os.chdir(root)
    needed=['telegram_market_report.py','telegram_report_pdf.py','stockbit_read.mjs']
    missing=[p for p in needed if not (root/p).is_file()]
    if not (root.parent/'stockbit_runtime/node-v22.23.3-win-arm64/node.exe').is_file():missing.append('Windows ARM64 Node runtime')
    if not (root.parent/'stockbit-mcp/dist/src/core/bars.js').is_file():missing.append('Stockbit MCP build')
    if importlib.util.find_spec('pypdf') is None:missing.append('pypdf')
    if os.getenv('ROWLET_S3_BUCKET') and importlib.util.find_spec('boto3') is None:missing.append('boto3')
    if missing:print(json.dumps({'ready':False,'missing':missing}));return 2
    if args.check:print(json.dumps({'ready':True,'note':'Local files checked only; login/network not tested.'}));return 0
    from idx_storage import acquire_instance_lock,save_json
    now=datetime.now(ZoneInfo('Asia/Jakarta'));session=now.date().isoformat()
    directory=root/'output/daily';directory.mkdir(parents=True,exist_ok=True)
    status={'attempted_at':now.isoformat(),'requested_session':session}
    def state(name):
        status['state']=name;save_json(directory/'status.json',status)
        try:configured_store(directory/'published').put('status.json',json.dumps(status).encode(),'application/json')
        except Exception:pass # Retain local status if delivery is down; never leak credentials in errors.
    if now.weekday()>4 or now.hour<19:state('outside_schedule');return 0
    handle=None
    try:
        handle=acquire_instance_lock(directory/'job-lock');state('running')
        from stockbit_data import query
        try:query('quote','BBCA')
        except Exception as error:
            reason=str(error).lower()
            state('stockbit_login_required' if any(s in reason for s in ['401','403','login','sesi atau','verifikasi browser']) else 'stockbit_unavailable')
            return 3
        from telegram_market_report import collect_market
        from report_evidence import enrich
        from telegram_report_pdf import export_pdf
        report=collect_market(now=now,progress=lambda s:print(s,flush=True));validate(report,session)
        checkpoint=directory/(session+'.json');save_json(checkpoint,finite(report))
        from threading import Event
        auth_failed=Event()
        def checked_query(*args,**kwargs):
            if auth_failed.is_set():raise ValueError('Stockbit 401; login required')
            try:return query(*args,**kwargs)
            except Exception as error:
                if any(s in str(error).lower() for s in ['401','403','login','sesi atau','verifikasi browser']):auth_failed.set()
                raise
        def one(row):enrich({'buy_signals':[row]},query_fn=checked_query);return row['ticker']
        with ThreadPoolExecutor(max_workers=3) as pool:
            for future in as_completed([pool.submit(one,r) for r in report['buy_signals']]):print('Evidence ready:',future.result(),flush=True)
        save_json(checkpoint,finite(report))
        if auth_failed.is_set():state('stockbit_login_required');return 3
        pdf=directory/(session+'.pdf');export_pdf(report,pdf)
        from pypdf import PdfReader
        reader=PdfReader(pdf)
        if not reader.pages:raise ValueError('empty_pdf')
        summary={'session':session,'created':report['created'],'aligned':report['aligned'],'requested':report['requested'],'new_buy':[r['ticker'] for r in report['buy_signals']],'pages':len(reader.pages)}
        # Only the report PDF and this public-market summary leave the PC.
        store=configured_store(directory/'published');publish(store,session,pdf.read_bytes(),summary)
        state('ready');print(json.dumps(summary));return 0
    except Exception as error:
        state('data_not_ready' if isinstance(error,ValueError) else 'failed')
        print('Daily report failed; previous latest preserved. See output/daily/status.json.');return 1
    finally:
        if handle:handle.close()
if __name__=='__main__':sys.exit(main())
