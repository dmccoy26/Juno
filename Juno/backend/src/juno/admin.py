"""Local administrator provisioning; no public registration endpoint."""
import argparse
import json
import os
from pathlib import Path
from .auth import provision
from .database import engine_for, sessions
from .models import Device


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    new = sub.add_parser('provision')
    new.add_argument('--label', required=True)
    new.add_argument('--owner-id')
    new.add_argument('--output', type=Path, required=True)
    revoke = sub.add_parser('revoke')
    revoke.add_argument('device_id')
    args = parser.parse_args()
    factory = sessions(engine_for())
    with factory() as session:
        if args.command == 'revoke':
            device = session.get(Device, args.device_id)
            if device is None:
                parser.error('Unknown device.')
            device.revoked = True
            session.commit()
            print('Device revoked.')
            return
        if not 1 <= len(args.label.strip()) <= 200:
            parser.error('Label must contain 1–200 characters.')
        # Reserve a new private output before creating database credentials.
        fd = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, 'w') as output:
                device, token = provision(session, args.label, args.owner_id)
                json.dump({'device_id': device.id, 'owner_id': device.owner_id, 'token': token}, output)
                output.flush()
                os.fsync(output.fileno())
                session.commit()
        except BaseException:
            args.output.unlink(missing_ok=True)
            raise
        print(f'Credential saved to {args.output}; keep this file private.')


if __name__ == '__main__':
    main()
