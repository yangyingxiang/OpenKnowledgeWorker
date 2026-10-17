#!/usr/bin/env python3
"""Load domain packs (examples/<pack>/pack.json) into the database.

    python seed.py                       # every pack in examples/, with sample outputs
    python seed.py mortgage-income-verification
    python seed.py --if-empty            # only when no process exists yet (used by Docker)
    python seed.py --no-sample-outputs   # sources + test cases only; run research yourself

Run from backend/ after `alembic upgrade head`.
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app  # noqa: E402
from app.extensions import get_db  # noqa: E402
from app.models import Process  # noqa: E402
from app.services.domain_packs import find_pack, install_pack, list_packs, load_pack, packs_dir  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('packs', nargs='*', help='pack ids (folder names); default: all packs')
    parser.add_argument('--no-sample-outputs', action='store_true', help='skip the sample PDD/knowledge/questions')
    parser.add_argument('--if-empty', action='store_true', help='do nothing if any process already exists')
    args = parser.parse_args(argv)

    app = create_app()
    with app.app_context():
        if args.if_empty and get_db().query(Process).first():
            print('Database already has processes; skipping seed.')
            return 0
        base = packs_dir(app.config)
        pack_ids = args.packs or [p['id'] for p in list_packs(base)]
        if not pack_ids:
            print(f'No domain packs found in {base}')
            return 1
        for pack_id in pack_ids:
            pack = load_pack(find_pack(base, pack_id))
            process = install_pack(pack, with_sample_outputs=not args.no_sample_outputs)
            print(f'Loaded domain pack "{pack_id}" as process {process.id} ({process.name})')
    return 0


if __name__ == '__main__':
    sys.exit(main())
