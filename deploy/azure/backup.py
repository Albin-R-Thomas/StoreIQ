"""SQLite online backup uploaded to Blob Storage using the VM managed identity."""
import datetime
import json
import os
from pathlib import Path
import sqlite3
import urllib.request


def main():
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination = Path('/opt/storeiq/backups') / f'storeiq-{stamp}.db'
    database = Path('/opt/storeiq/data/store-iq.db')
    if not database.is_file():
        raise SystemExit('Database is missing; refusing to back up an empty database')
    with sqlite3.connect(database) as source, sqlite3.connect(destination) as target:
        source.backup(target)
        if target.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
            raise RuntimeError('Backup failed SQLite integrity check')
    os.chmod(destination, 0o600)
    request = urllib.request.Request(
        'http://169.254.169.254/metadata/identity/oauth2/token'
        '?api-version=2018-02-01&resource=https%3A%2F%2Fstorage.azure.com%2F',
        headers={'Metadata': 'true'},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        token = json.load(response)['access_token']
    url = os.environ['STOREIQ_BACKUP_URL'].rstrip('/') + '/' + destination.name
    upload = urllib.request.Request(
        url, data=destination.read_bytes(), method='PUT', headers={
            'Authorization': 'Bearer ' + token,
            'x-ms-version': '2023-11-03',
            'x-ms-blob-type': 'BlockBlob',
            'Content-Type': 'application/octet-stream',
        },
    )
    with urllib.request.urlopen(upload, timeout=120) as response:
        if response.status != 201:
            raise RuntimeError('Backup upload was not accepted')
    cutoff = datetime.datetime.now().timestamp() - 7 * 86400
    for old in destination.parent.glob('*.db'):
        if old.stat().st_mtime < cutoff:
            old.unlink()
    print('Verified and uploaded backup:', destination.name)


if __name__ == '__main__':
    main()
