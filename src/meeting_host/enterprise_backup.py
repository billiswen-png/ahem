"""Local encrypted snapshots. Restore only to a new file, never a live DB."""
import argparse
import os
from pathlib import Path
import sqlite3

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from .security import EnvelopeStore, load_kek

MAGIC = b'AHEM-BACKUP-1\n'
MAX_BYTES = 64 * 1024 * 1024


def write_new(path, data):
    path = Path(path)
    if not path.parent.is_dir() or path.parent.is_symlink() or path.parent.stat().st_mode & 0o077:
        raise ValueError('Destination directory must already exist and be private (0700)')
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


def validate(db, key):
    if db.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
        raise ValueError('SQLite integrity check failed')
    tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {'meetings','grants','disabled_members','audit'} <= tables:
        raise ValueError('Not a supported enterprise database')
    store = EnvelopeStore(key)
    count = 0
    for mid, blob in db.execute('SELECT id,blob FROM meetings'):
        # This offline local-admin CLI requires possession of the private KEK.
        store.decrypt_text(blob, meeting_id=mid, artifact_type='events', purpose='backup integrity verification', operator=True)
        count += 1
    return count


def snapshot(source, destination, key):
    source = Path(source)
    if source.is_symlink() or not source.is_file() or source.stat().st_size > MAX_BYTES:
        raise ValueError('Expected a regular database under 64 MiB')
    db = sqlite3.connect(':memory:')
    try:
        origin = sqlite3.connect(source.resolve().as_uri()+'?mode=ro', uri=True)
        try:
            origin.backup(db)
        finally:
            origin.close()
        count = validate(db,key)
        raw = db.serialize()
        if len(raw) > MAX_BYTES:
            raise ValueError('Snapshot exceeds 64 MiB')
        nonce = os.urandom(12)
        write_new(destination, MAGIC+nonce+AESGCM(key).encrypt(nonce,raw,MAGIC))
        return count
    finally:
        db.close()


def restore(source, key, destination=None):
    source = Path(source)
    if source.is_symlink() or source.stat().st_size > MAX_BYTES+128:
        raise ValueError('Invalid backup file')
    data = source.read_bytes()
    if not data.startswith(MAGIC):
        raise ValueError('Unknown backup format')
    nonce = data[len(MAGIC):len(MAGIC)+12]
    raw = AESGCM(key).decrypt(nonce,data[len(MAGIC)+12:],MAGIC)
    db = sqlite3.connect(':memory:')
    try:
        db.deserialize(raw)
        count = validate(db,key)
        if destination is not None:
            write_new(destination, db.serialize())
        return count
    finally:
        db.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['backup','verify','restore'])
    parser.add_argument('--source',type=Path,required=True)
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args()
    if args.action != 'verify' and args.destination is None:
        parser.error('--destination is required; it must not exist')
    key=load_kek()
    count = snapshot(args.source,args.destination,key) if args.action=='backup' else restore(args.source,key,args.destination if args.action=='restore' else None)
    print(f'{args.action}: PASS; integrity and {count} encrypted meeting records verified')


if __name__=='__main__':
    main()
