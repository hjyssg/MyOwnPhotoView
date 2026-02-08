import io
import ipaddress
import os
import socket

import qrcode


def _is_private_ipv4(value: str) -> bool:
    try:
        ip = ipaddress.ip_address(value)
        return isinstance(ip, ipaddress.IPv4Address) and (ip.is_private or ip.is_loopback)
    except Exception:
        return False


def collect_local_ipv4_candidates() -> list[str]:
    candidates = set()

    try:
        host_name = socket.gethostname()
        _, _, addrs = socket.gethostbyname_ex(host_name)
        for ip in addrs:
            if _is_private_ipv4(ip):
                candidates.add(ip)
    except Exception:
        pass

    try:
        infos = socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET)
        for info in infos:
            ip = info[4][0]
            if _is_private_ipv4(ip):
                candidates.add(ip)
    except Exception:
        pass

    return sorted(candidates)


def build_access_url_candidates(request) -> list[str]:
    urls = []
    seen = set()

    def push(url: str):
        if not url or url in seen:
            return
        seen.add(url)
        urls.append(url)

    frontend_port = os.getenv('FRONTEND_PORT', '3000').strip() or '3000'
    frontend_scheme = os.getenv('FRONTEND_SCHEME', 'http').strip() or 'http'
    frontend_host = os.getenv('FRONTEND_HOST', '').strip()
    if frontend_host:
        push(f'{frontend_scheme}://{frontend_host}:{frontend_port}')

    host = (request.url.hostname or '').strip()
    if host and host not in ('localhost', '127.0.0.1'):
        push(f'http://{host}:{frontend_port}')

    for ip in collect_local_ipv4_candidates():
        if ip != '127.0.0.1':
            push(f'http://{ip}:{frontend_port}')

    push('http://localhost:3000')
    return urls


def build_qrcode_png(content: str) -> io.BytesIO:
    qr_img = qrcode.make(content)
    buffer = io.BytesIO()
    qr_img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer
