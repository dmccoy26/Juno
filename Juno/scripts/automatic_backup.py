"""Encrypted, restore-checked work-Mac backups. No live database file copies."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone, timedelta
import fcntl
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tarfile
import tempfile
import uuid
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

MAGIC=b'JUNO-BACKUP-1\n'
CHUNK=1024*1024


def run(*args, **kwargs):
    return subprocess.run([str(x) for x in args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,**kwargs)


def file_hash(path):
    h=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(CHUNK),b''):h.update(block)
    return h.hexdigest()


def encrypt(source,destination,key):
    nonce=secrets.token_bytes(12);header=MAGIC+nonce
    enc=Cipher(algorithms.AES(key),modes.GCM(nonce)).encryptor();enc.authenticate_additional_data(header)
    with source.open('rb') as src,destination.open('xb') as out:
        out.write(header)
        for block in iter(lambda:src.read(CHUNK),b''):out.write(enc.update(block))
        out.write(enc.finalize());out.write(enc.tag);out.flush();os.fsync(out.fileno())


def decrypt(source,destination,key):
    with source.open('rb') as src,destination.open('xb') as out:
        header=src.read(len(MAGIC)+12)
        if not header.startswith(MAGIC) or source.stat().st_size<len(header)+16:raise ValueError('Invalid backup format')
        src.seek(-16,2);tag=src.read(16);remaining=source.stat().st_size-len(header)-16;src.seek(len(header))
        dec=Cipher(algorithms.AES(key),modes.GCM(header[len(MAGIC):],tag)).decryptor();dec.authenticate_additional_data(header)
        while remaining:
            block=src.read(min(CHUNK,remaining))
            if not block:raise ValueError('Incomplete encrypted backup')
            remaining-=len(block);out.write(dec.update(block))
        out.write(dec.finalize())


def retained(names,now):
    """Keep 48 newest snapshots, plus one per day/month inside rolling limits."""
    ordered=sorted(names,reverse=True);keep=set(ordered[:48]);days=set();months=set()
    for name in ordered:
        try:stamp=datetime.strptime(name,'juno-%Y%m%dT%H%M%S%fZ.junobak').replace(tzinfo=timezone.utc)
        except ValueError:continue
        day=stamp.date();month=(stamp.year,stamp.month)
        if stamp>=now-timedelta(days=30) and day not in days:keep.add(name);days.add(day)
        if (now.year-stamp.year)*12+now.month-stamp.month<12 and month not in months:keep.add(name);months.add(month)
    return keep


def state_files(state):
    result=[]
    owner=state/'desktop-owner.json'
    if not owner.is_file() or owner.is_symlink():raise ValueError('Work-Mac identity is missing')
    result.append(owner)
    for name in ('workspace-identity.json', 'last-successful-release.json'):
        path=state/name
        if path.is_symlink():raise ValueError('Symlinked workspace identity is unsupported')
        if path.is_file():result.append(path)
    for folder in ('shared-host','worker-portal','offline-copies'):
        directory=state/folder
        if directory.is_symlink():raise ValueError('Symlinked recovery directory is unsupported')
        if directory.exists():
            for path in directory.rglob('*'):
                if path.is_symlink():raise ValueError('Symlinked recovery file is unsupported')
                if path.is_file():result.append(path)
    return sorted(result)


@contextmanager
def database(config):
    state=Path(config['state']);pg=Path(config['postgres_bin']);started=False;lock=None
    ready=lambda:subprocess.run([str(pg/'pg_isready'),'-h',str(state/'postgres/socket'),'-U','juno','-d','juno_dev'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
    try:
        if not ready():
            # Match the desktop helper's lock so it cannot launch midway through a cold backup.
            lock=(state/'desktop.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            if not ready():
                run(pg/'pg_ctl','-D',state/'postgres/data','-l',state/'postgres/postgres.log','-w','-t','30','start');started=True
        yield pg,state/'postgres/socket'
    finally:
        if started:run(pg/'pg_ctl','-D',state/'postgres/data','-m','fast','-w','stop')
        if lock:lock.close()


def restore_check(pg,socket,dump,owner):
    name='juno_backup_verify_'+uuid.uuid4().hex
    run(pg/'createdb','-h',socket,'-U','juno',name)
    try:
        run(pg/'pg_restore','--exit-on-error','--no-owner','--no-privileges','-h',socket,'-U','juno','-d',name,dump)
        sql="SELECT version_num FROM alembic_version; SELECT count(*) FROM owners WHERE id='"+str(uuid.UUID(owner))+"';"
        result=run(pg/'psql','-X','-A','-t','-h',socket,'-U','juno','-d',name,'-c',sql).stdout.decode().splitlines()
        if len(result)!=2 or result[1]!='1':raise ValueError('Restored backup did not contain the work owner')
        return result[0]
    finally:run(pg/'dropdb','-h',socket,'-U','juno',name)


def destination(config):
    volume=Path(config['volume']);target=Path(config['destination'])
    if not volume.is_mount() or volume.is_symlink():raise ValueError('Backup volume is not mounted; no fallback directory was created')
    if target.is_symlink() or not target.resolve().is_relative_to(volume.resolve()):raise ValueError('Invalid destination')
    marker=target/'.juno-destination-id'
    if not marker.is_file() or marker.read_text().strip()!=config['destination_id']:raise ValueError('Backup destination identity does not match')
    return target


def backup(config):
    target=destination(config);state=Path(config['state']);key=Path(config['key_file']).read_bytes()
    if len(key)!=32:raise ValueError('Invalid recovery key')
    with tempfile.TemporaryDirectory(prefix='juno-backup-',dir=config['temporary_root']) as temporary:
        work=Path(temporary);os.chmod(work,0o700);files=state_files(state);before={str(p.relative_to(state)):file_hash(p) for p in files}
        owner=json.loads((state/'desktop-owner.json').read_text())['owner_id'];dump=work/'database.dump'
        with database(config) as (pg,socket):
            run(pg/'pg_dump','-h',socket,'-U','juno','-d','juno_dev','--format=custom','--file',dump)
            schema=restore_check(pg,socket,dump,owner)
        recovery=work/'recovery';recovery.mkdir(mode=0o700)
        for path in files:
            relative=path.relative_to(state);out=recovery/relative;out.parent.mkdir(parents=True,exist_ok=True,mode=0o700);shutil.copyfile(path,out);out.chmod(0o600)
        if before!={str(p.relative_to(state)):file_hash(p) for p in state_files(state)}:raise ValueError('Recovery settings changed during backup; retry safely')
        for relative,digest in before.items():
            if file_hash(recovery/relative)!=digest:raise ValueError('Recovery copy mismatch')
        manifest={'format':1,'created_at':datetime.now(timezone.utc).isoformat(),'schema':schema,'database':'database.dump','database_sha256':file_hash(dump),'recovery_sha256':before,'restore_tested':True,'source_state':str(state),'keychain_included':False}
        (work/'manifest.json').write_text(json.dumps(manifest,indent=2))
        archive=work/'backup.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            for name in ('database.dump','manifest.json','recovery'):tar.add(work/name,arcname=name)
        encrypted=work/'encrypted';encrypt(archive,encrypted,key)
        name='juno-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.junobak'
        partial=target/('.'+name+'.partial');final=target/name
        try:
            shutil.copyfile(encrypted,partial)
            if file_hash(partial)!=file_hash(encrypted):raise ValueError('Network backup checksum mismatch')
            verified=work/'verified.tar.gz';decrypt(partial,verified,key)
            if file_hash(verified)!=file_hash(archive):raise ValueError('Network backup authentication mismatch')
            partial.rename(final)
            (target/(name+'.sha256')).write_text(file_hash(final)+'  '+name+'\n')
        finally:
            if partial.exists():partial.unlink()
        # Never touch files outside our own strict generated naming scheme, nor prune before success.
        names=[p.name for p in target.glob('juno-*.junobak') if p.is_file() and not p.is_symlink()]
        keep=retained(names,datetime.now(timezone.utc))
        for old in set(names)-keep:
            try:datetime.strptime(old,'juno-%Y%m%dT%H%M%S%fZ.junobak')
            except ValueError:continue
            (target/old).unlink();checksum=target/(old+'.sha256')
            if checksum.is_file() and not checksum.is_symlink():checksum.unlink()
        return {'status':'success','completed_at':datetime.now(timezone.utc).isoformat(),'backup':str(final),'bytes':final.stat().st_size,'restore_tested':True,'schema':schema}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--extract',type=Path,help='Authenticate and extract an archive; does not restore any database')
    parser.add_argument('--output',type=Path);args=parser.parse_args();config=json.loads(args.config.read_text());os.umask(0o077)
    with (Path(config['temporary_root'])/'backup.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:print('Another Juno backup is running.');return
        if args.extract:
            if not args.output or args.output.exists():parser.error('--output must name a new directory')
            with tempfile.TemporaryDirectory(dir=config['temporary_root']) as temporary:
                plain=Path(temporary)/'archive.tar.gz';decrypt(args.extract,plain,Path(config['key_file']).read_bytes())
                args.output.mkdir(mode=0o700,parents=True)
                with tarfile.open(plain) as tar:tar.extractall(args.output,filter='data')
            print('Authenticated backup extracted. No live database was modified.');return
        try:status=backup(config)
        except Exception as error:
            # Subprocess stderr may contain work data; record only safe error class/command.
            message=('Command failed: '+Path(str(error.cmd[0])).name) if isinstance(error,subprocess.CalledProcessError) else str(error)
            status={'status':'failed','attempted_at':datetime.now(timezone.utc).isoformat(),'reason':message}
            print(json.dumps(status));raise SystemExit(1)
        finally:
            if 'status' in locals():
                path=Path(config['status_file']);temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(status,indent=2));temporary.replace(path)
        print(json.dumps(status))


if __name__=='__main__':main()
