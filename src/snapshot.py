"""
BlackRoad Snapshot Service
Point-in-time snapshots for disaster recovery.
"""
import json, tarfile, hashlib
from pathlib import Path
from datetime import datetime

BLACKROAD_HOME = Path.home() / '.blackroad'
SNAPSHOT_DIR = BLACKROAD_HOME / 'snapshots'


def create_snapshot(label: str = 'manual') -> dict:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.utcnow().strftime('%Y%m%d-%H%M%S')
    name = f'blackroad-snapshot-{ts}-{label}'
    archive_path = SNAPSHOT_DIR / f'{name}.tar.gz'
    with tarfile.open(archive_path, 'w:gz') as tar:
        for item in ['memory', 'sessions', 'cece-identity.db']:
            target = BLACKROAD_HOME / item
            if target.exists():
                tar.add(target, arcname=item)
    checksum = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    manifest = {'name': name, 'timestamp': ts, 'label': label,
                'checksum': checksum, 'size_bytes': archive_path.stat().st_size}
    (SNAPSHOT_DIR / f'{name}.json').write_text(json.dumps(manifest, indent=2))
    return manifest


def list_snapshots() -> list:
    if not SNAPSHOT_DIR.exists():
        return []
    return [json.loads(f.read_text()) for f in sorted(SNAPSHOT_DIR.glob('*.json'))]


if __name__ == '__main__':
    snap = create_snapshot('cli')
    print(f"✓ Snapshot: {snap['name']} ({snap['size_bytes']:,} bytes)")
