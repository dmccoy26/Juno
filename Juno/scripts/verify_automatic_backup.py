"""Exercise backup cryptography, rotation and offline-destination safety with fictional data."""
from datetime import datetime,timedelta,timezone
import importlib.util
from pathlib import Path
import tempfile
spec=importlib.util.spec_from_file_location('backup',Path(__file__).with_name('automatic_backup.py'));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory);source=root/'plain';source.write_bytes(b'Synthetic diary and worker report\n'*100000)
    key=bytes(range(32));encrypted=root/'encrypted';m.encrypt(source,encrypted,key);restored=root/'restored';m.decrypt(encrypted,restored,key);assert m.file_hash(source)==m.file_hash(restored)
    damaged=bytearray(encrypted.read_bytes());damaged[len(m.MAGIC)+20]^=1;(root/'damaged').write_bytes(damaged)
    try:m.decrypt(root/'damaged',root/'rejected',key)
    except Exception:pass
    else:raise AssertionError('Tampered ciphertext accepted')
    try:m.decrypt(encrypted,root/'wrong-key',bytes(reversed(key)))
    except Exception:pass
    else:raise AssertionError('Wrong key accepted')
    absent=root/'absent'
    try:m.destination({'volume':str(absent),'destination':str(absent/'Juno Backups'),'destination_id':'synthetic'})
    except ValueError:pass
    else:raise AssertionError('Unmounted destination accepted')
    assert not absent.exists()
    state=root/'state';state.mkdir()
    for name in ('desktop-owner.json','workspace-identity.json','last-successful-release.json'):
        (state/name).write_text('{}')
    assert {p.name for p in m.state_files(state)}=={'desktop-owner.json','workspace-identity.json','last-successful-release.json'}
    (state/'workspace-identity.json').unlink();(state/'workspace-identity.json').symlink_to(state/'desktop-owner.json')
    try:m.state_files(state)
    except ValueError:pass
    else:raise AssertionError('Symlinked workspace pin accepted')
    now=datetime(2026,11,2,tzinfo=timezone.utc)
    names=['juno-'+(now-timedelta(hours=i)).strftime('%Y%m%dT%H%M%S%fZ')+'.junobak' for i in range(24*400)]
    kept=m.retained(names,now);assert set(names[:48])<=kept
    assert len(kept)<100 and names[-1] not in kept
    for i in range(30):assert any(datetime.strptime(n,'juno-%Y%m%dT%H%M%S%fZ.junobak').date()==(now-timedelta(days=i)).date() for n in kept)
print('PASS authenticated encryption round-trip, tamper/wrong-key rejection, 48-hour/30-day/12-month retention and no missing-drive fallback.')
