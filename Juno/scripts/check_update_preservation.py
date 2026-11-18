"""Capture/compare private record fingerprints before and after a Juno update.

Run while work is paused, against the actual active workspace. No record text or
credentials are printed. A difference requires review; this tool never repairs,
resets or deletes records. Keep the baseline outside Git.
"""
import argparse
import json
import os
from pathlib import Path
import psycopg
from psycopg import sql


def capture(state, projection=None):
    state=state.resolve()
    owner=json.loads((state/'desktop-owner.json').read_text())['owner_id']
    with psycopg.connect(host=str(state/'postgres/socket'),user='juno',dbname='juno_dev') as connection:
        connection.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
        tables=connection.execute("select tablename from pg_tables where schemaname='public' and tablename not in ('devices','alembic_version') order by tablename").fetchall()
        rows={};columns={}
        for (name,) in tables:
            current=[r[0] for r in connection.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name=%s ORDER BY ordinal_position",(name,))]
            fields=(projection or {}).get(name,current)
            if not fields or not set(fields).issubset(current):
                raise ValueError('Previously saved columns are missing in '+name+'.')
            query=sql.SQL('select md5(row_to_json(r)::text) from (select {} from {}) r order by 1').format(sql.SQL(',').join(map(sql.Identifier,fields)),sql.Identifier(name))
            rows[name]=[r[0] for r in connection.execute(query)]
            columns[name]=fields
        # Device credentials rotate normally. Previously paired identities must still exist.
        devices=[r[0] for r in connection.execute('select id from devices order by id')]
    return {'format':2,'workspace':str(state),'owner':owner,'rows':rows,'columns':columns,'devices':devices}


def compare(before,after):
    if before['workspace']!=after['workspace'] or before['owner']!=after['owner']:
        raise ValueError('Workspace location or owner changed; stop delivery and review recovery.')
    for name,rows in before['rows'].items():
        if rows!=after['rows'].get(name):
            raise ValueError('Record fingerprints changed in '+name+'; review expected migration/work changes before accepting this update.')
    if not set(before['devices']).issubset(after['devices']):
        raise ValueError('Existing paired/device identities are missing.')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('capture','verify'))
    p.add_argument('--state',type=Path,default=Path.home()/'Library/Application Support/Juno')
    p.add_argument('--baseline',type=Path,required=True)
    args=p.parse_args()
    if args.command=='capture':
        current=capture(args.state)
        fd=os.open(args.baseline,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,'w') as output:json.dump(current,output)
        print('Private preservation baseline saved. Work content was not printed.')
    else:
        before=json.loads(args.baseline.read_text())
        current=capture(args.state,before.get('columns'))
        compare(before,current)
        print('PASS same workspace/owner, unchanged work records and retained device identities.')


if __name__=='__main__':main()
