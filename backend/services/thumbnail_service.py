import hashlib
import logging
import subprocess
from pathlib import Path

from PIL import Image, ImageOps

from backend.core.config import THUMBNAIL_DIR

try:
    import xxhash
except ImportError:  # pragma: no cover
    xxhash = None


logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.heic']
SUPPORTED_VIDEO_EXTENSIONS = ['.mp4', '.mov', '.avi']
THUMBNAIL_DIR_PATH = Path(THUMBNAIL_DIR)


def _filename_fingerprint(filepath: Path) -> str:
    return hashlib.md5(str(filepath.resolve()).encode()).hexdigest()


def _run_command(command):
    try:
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
            encoding='utf-8',
            errors='ignore',
        )
    except FileNotFoundError:
        return None


def hash_file_sampled(filepath: Path) -> str:
    """Fast content fingerprint using sampled bytes (head/middle/tail)."""
    sample_size = 64 * 1024
    small_file_threshold = 3 * 1024 * 1024

    if xxhash is not None:
        hasher = xxhash.xxh64()
    else:
        hasher = hashlib.blake2b(digest_size=16)

    try:
        file_size = filepath.stat().st_size
    except Exception:
        return _filename_fingerprint(filepath)

    hasher.update(str(file_size).encode('utf-8'))

    with filepath.open('rb') as f:
        if file_size <= small_file_threshold:
            for chunk in iter(lambda: f.read(1024 * 1024), b''):
                hasher.update(chunk)
            return hasher.hexdigest()

        f.seek(0)
        hasher.update(f.read(sample_size))

        middle_offset = max(0, (file_size // 2) - (sample_size // 2))
        f.seek(middle_offset)
        hasher.update(f.read(sample_size))

        tail_offset = max(0, file_size - sample_size)
        f.seek(tail_offset)
        hasher.update(f.read(sample_size))

    return hasher.hexdigest()


def generate_image_thumbnail(filepath: Path, thumbnail_path: Path):
    with Image.open(filepath) as img_raw:
        img = ImageOps.exif_transpose(img_raw)
        original_mode = img.mode

        if img.mode in ('RGBA', 'LA'):
            rgba = img.convert('RGBA')
            background = Image.new('RGB', rgba.size, (255, 255, 255))
            background.paste(rgba, mask=rgba.split()[-1])
            img = background
        elif img.mode == 'P':
            if 'transparency' in img.info:
                rgba = img.convert('RGBA')
                background = Image.new('RGB', rgba.size, (255, 255, 255))
                background.paste(rgba, mask=rgba.split()[-1])
                img = background
            else:
                img = img.convert('RGB')
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        img.thumbnail((400, 400))
        img.save(thumbnail_path, 'JPEG', quality=85, optimize=True)

        if original_mode != img.mode:
            logger.debug(
                'Thumbnail mode converted for JPEG save. filepath=%s mode_before=%s mode_after=%s',
                str(filepath),
                original_mode,
                img.mode,
            )


def create_video_thumbnail(video_path: Path, thumbnail_path: Path):
    def _thumbnail_ready() -> bool:
        return thumbnail_path.exists() and thumbnail_path.stat().st_size > 0

    attempts = [
        [
            'ffmpeg',
            '-y',
            '-i',
            str(video_path),
            '-vf',
            'select=eq(n\\,1)',
            '-vframes',
            '1',
            str(thumbnail_path),
        ],
        [
            'ffmpeg',
            '-y',
            '-i',
            str(video_path),
            '-vf',
            'select=eq(n\\,0)',
            '-vframes',
            '1',
            str(thumbnail_path),
        ],
        [
            'ffmpeg',
            '-y',
            '-ss',
            '00:00:00',
            '-i',
            str(video_path),
            '-frames:v',
            '1',
            str(thumbnail_path),
        ],
    ]

    last_err = ''
    for command in attempts:
        result = _run_command(command)
        if result is None:
            last_err = 'ffmpeg not found'
            break

        if _thumbnail_ready():
            return

        if result.stderr:
            last_err = result.stderr.strip()

    logger.error(
        'Failed to generate video thumbnail. video_path=%s thumbnail_path=%s last_err=%s',
        str(video_path),
        str(thumbnail_path),
        (last_err[:500] if last_err else 'unknown error'),
    )
