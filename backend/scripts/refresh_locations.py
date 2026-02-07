import argparse
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.database import SessionLocal, MediaItem
from backend.scanner import _is_valid_coordinate, reverse_geocode_location, _is_under_directory


def refresh_locations(
    directory: str | None = None,
    dry_run: bool = False,
    progress_interval: int = 100,
) -> dict:
    db = SessionLocal()
    updated = 0
    cleared = 0
    skipped = 0
    start_time = time.time()

    try:
        query = db.query(MediaItem).filter(MediaItem.media_type == 'image')
        if directory:
            abs_dir = os.path.abspath(directory)
            query = [item for item in query.all() if _is_under_directory(item.filepath, abs_dir)]
        else:
            query = query.all()

        total = len(query)
        for index, item in enumerate(query, start=1):
            lat = item.latitude
            lon = item.longitude

            if not _is_valid_coordinate(lat, lon):
                if item.location_name is not None:
                    if not dry_run:
                        item.location_name = None
                    cleared += 1
                else:
                    skipped += 1
                continue

            refreshed = reverse_geocode_location(lat, lon)
            if refreshed != item.location_name:
                if not dry_run:
                    item.location_name = refreshed
                updated += 1
            else:
                skipped += 1

            if progress_interval > 0 and index % progress_interval == 0:
                elapsed = time.time() - start_time
                print(
                    f'Progress: {index}/{total} '
                    f'(updated={updated}, cleared={cleared}, skipped={skipped}) '
                    f'elapsed={elapsed:.1f}s'
                )

        if not dry_run:
            db.commit()
    finally:
        db.close()

    return {
        'updated': updated,
        'cleared': cleared,
        'skipped': skipped,
        'dry_run': dry_run,
        'total': total,
        'elapsed_seconds': time.time() - start_time,
    }


def main():
    parser = argparse.ArgumentParser(description='Refresh reverse geocoded location names.')
    parser.add_argument(
        '--directory',
        help='Only refresh items under this directory. If omitted, process all items.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without writing to the database.',
    )
    parser.add_argument(
        '--progress-interval',
        type=int,
        default=100,
        help='Print progress every N items (0 to disable).',
    )
    args = parser.parse_args()

    result = refresh_locations(
        directory=args.directory,
        dry_run=args.dry_run,
        progress_interval=args.progress_interval,
    )
    print(
        'Refresh complete. '
        f"Updated: {result['updated']}, Cleared: {result['cleared']}, "
        f"Skipped: {result['skipped']}, Dry-run: {result['dry_run']}, "
        f"Total: {result['total']}, Elapsed: {result['elapsed_seconds']:.1f}s"
    )


if __name__ == '__main__':
    main()