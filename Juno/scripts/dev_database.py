"""Start/stop a Juno-only PostgreSQL cluster. Unix socket only; no TCP listener."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / '.local' / 'postgres'
DATA = STATE / 'data'
SOCKET = STATE / 'socket'
BIN = Path('/opt/homebrew/opt/postgresql@17/bin')


def run(*args):
    subprocess.run([str(BIN / args[0]), *map(str, args[1:])], check=True,
                   stdout=subprocess.DEVNULL)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['start', 'stop', 'url'])
    args = parser.parse_args()
    if args.command == 'url':
        print(f'postgresql+psycopg://juno@/juno_dev?host={SOCKET}')
        return
    if args.command == 'stop':
        run('pg_ctl', '-D', DATA, '-m', 'fast', 'stop')
        print('Juno development database stopped.')
        return
    if not (BIN / 'initdb').is_file():
        parser.error('Install postgresql@17 with Homebrew first.')
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    STATE.chmod(0o700)
    SOCKET.mkdir(exist_ok=True, mode=0o700)
    SOCKET.chmod(0o700)
    if not (DATA / 'PG_VERSION').exists():
        run('initdb', '-D', DATA, '-U', 'juno', '--auth-local=trust',
            '--auth-host=reject', '--encoding=UTF8', '--no-locale')
        with (DATA / 'postgresql.conf').open('a') as config:
            config.write("\nlisten_addresses = ''\n")
            config.write(f"unix_socket_directories = '{SOCKET}'\n")
            config.write('unix_socket_permissions = 0700\n')
    status = subprocess.run([str(BIN / 'pg_ctl'), '-D', str(DATA), 'status'],
                            stdout=subprocess.DEVNULL).returncode
    if status != 0:
        run('pg_ctl', '-D', DATA, '-l', STATE / 'postgres.log', 'start')
    # Check before creating; never reset or drop an existing development DB.
    result = subprocess.check_output([str(BIN / 'psql'), '-h', str(SOCKET), '-U', 'juno',
              '-d', 'postgres', '-Atc', "SELECT 1 FROM pg_database WHERE datname='juno_dev'"])
    if not result.strip():
        run('createdb', '-h', SOCKET, '-U', 'juno', 'juno_dev')
    print('Juno development database ready (private Unix socket; synthetic data only).')


if __name__ == '__main__':
    main()
