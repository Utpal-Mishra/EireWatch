import argparse
import hashlib
import json
from pathlib import Path
from .core import Monitor
from .collectors import collect
from .report import render


def main():
    parser=argparse.ArgumentParser(description='ÉireWatch private monitoring CLI')
    parser.add_argument('--db',default='eirewatch.sqlite')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('collect');p.add_argument('config')
    p=sub.add_parser('import');p.add_argument('config');p.add_argument('payload')
    p=sub.add_parser('review');p.add_argument('id');p.add_argument('revision',type=int);p.add_argument('decision',choices=['approved','rejected']);p.add_argument('--actor',required=True)
    p=sub.add_parser('subscribe');p.add_argument('id');p.add_argument('--areas',nargs='*',default=[]);p.add_argument('--categories',nargs='*',default=[]);p.add_argument('--disable',action='store_true')
    sub.add_parser('queue')
    p=sub.add_parser('inbox');p.add_argument('id')
    p=sub.add_parser('ack');p.add_argument('id');p.add_argument('--subscription',required=True)
    sub.add_parser('health')
    p=sub.add_parser('export');p.add_argument('output');p.add_argument('--html',action='store_true')
    args=parser.parse_args();m=Monitor(args.db)
    try:
        if args.command in ('collect','import'):
            configs=json.loads(Path(args.config).read_text())
            if args.command=='collect':
                result={c['id']:collect(m,c) for c in configs}
            else:
                if len(configs)!=1: raise ValueError('Import requires one source')
                raw=Path(args.payload).read_bytes();payload=json.loads(raw)
                if payload.get('schema_version')!=1:raise ValueError('Unsupported schema')
                m.register(configs[0]);result=m.ingest(configs[0]['id'],payload['incidents'],raw_hash=hashlib.sha256(raw).hexdigest(),published=payload.get('published'))
        elif args.command=='review':result=m.review(args.id,args.revision,args.decision,args.actor)
        elif args.command=='subscribe':result=m.subscribe(args.id,args.areas,args.categories,not args.disable)
        elif args.command=='queue':result=m.queue()
        elif args.command=='inbox':result=m.inbox(args.id)
        elif args.command=='ack':result=m.acknowledge(args.id,args.subscription)
        elif args.command=='health':result=m.health()
        elif args.command=='export':
            snapshot=m.snapshot();Path(args.output).write_text(render(snapshot) if args.html else json.dumps(snapshot,indent=2));result={'written':args.output}
        print(json.dumps(result,indent=2))
    finally:m.db.close()

if __name__=='__main__':main()
