"""Small read-only local API check; not a capacity or audio latency benchmark."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
import math
from pathlib import Path
import platform
from http.cookies import SimpleCookie
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse

p=argparse.ArgumentParser()
p.add_argument('--url',required=True)
p.add_argument('--identities',type=Path,required=True)
p.add_argument('--output',type=Path,required=True)
p.add_argument('--requests',type=int,default=200)
p.add_argument('--concurrency',type=int,default=4)
args=p.parse_args()
if urlparse(args.url).hostname!='127.0.0.1' or not 1<=args.requests<=2000 or not 1<=args.concurrency<=8:
    p.error('Loopback only, <=2000 requests and <=8 workers')
base=args.url.rstrip('/')
actor=next(a for a in json.loads(args.identities.read_text()) if a['id']=='manager')
req=urllib.request.Request(base+'/api/login',data=json.dumps({'token':actor['token']}).encode(),headers={'Content-Type':'application/json','Origin':base})
with urllib.request.urlopen(req,timeout=10) as response:
    cookies=SimpleCookie(response.headers['Set-Cookie'])
cookie='enterprise='+cookies['enterprise'].value
headers={'Cookie':cookie}
with urllib.request.urlopen(urllib.request.Request(base+'/api/analytics',headers=headers),timeout=10) as response:
    count=json.load(response)['total_count']
def sample(_):
    start=time.perf_counter()
    try:
        with urllib.request.urlopen(urllib.request.Request(base+'/api/analytics',headers=headers),timeout=10) as response:
            response.read();status=response.status
    except urllib.error.HTTPError as exc:status=exc.code
    except (OSError,TimeoutError):status=0
    return (time.perf_counter()-start)*1000,status
start=time.perf_counter()
with ThreadPoolExecutor(max_workers=args.concurrency) as pool:results=list(pool.map(sample,range(args.requests)))
elapsed=time.perf_counter()-start
latencies=sorted(t for t,status in results if status==200)
result={'scope':'local read-only analytics API; not audio or production capacity','platform':platform.platform(),
    'python':platform.python_version(),'synthetic_meetings':count,'requests':args.requests,'concurrency':args.concurrency,
    'successes':len(latencies),'failures':len(results)-len(latencies),'elapsed_seconds':round(elapsed,3),
    'requests_per_second':round(len(results)/elapsed,2),'p50_ms':round(latencies[math.ceil(len(latencies)*.5)-1],3) if latencies else None,
    'p95_ms':round(latencies[math.ceil(len(latencies)*.95)-1],3) if latencies else None}
args.output.parent.mkdir(parents=True,exist_ok=True)
args.output.write_text(json.dumps(result,indent=2)+'\n')
urllib.request.urlopen(urllib.request.Request(base+'/api/logout',data=b'{}',headers={**headers,'Origin':base,'Content-Type':'application/json'}),timeout=10).close()
print(json.dumps(result,indent=2))
raise SystemExit(0 if not result['failures'] else 1)
