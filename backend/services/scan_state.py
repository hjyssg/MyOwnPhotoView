import datetime
import threading

scan_lock = threading.Lock()
scan_state = {
    'is_running': False,
    'directory': None,
    'current_folder': None,
    'current_file': None,
    'processed_files': 0,
    'total_files': 0,
    'current_folder_index': 0,
    'total_folders': 0,
    'stats': None,
    'started_at': None,
    'finished_at': None,
    'message': 'idle',
    'error': None,
}


def now_iso():
    return datetime.datetime.utcnow().isoformat() + 'Z'


def update_scan_state(**kwargs):
    with scan_lock:
        scan_state.update(kwargs)


def get_scan_state_copy():
    with scan_lock:
        return dict(scan_state)
