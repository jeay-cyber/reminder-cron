"""
reminder.py
-----------
Triggers the cron URL on InfinityFree, handling the JavaScript
anti-bot challenge by solving the AES cookie automatically.

No direct DB connection needed — works from GitHub Actions.

Requirements:
    pip install requests pycryptodome
"""

import os
import re
import sys
import logging
import requests
from Crypto.Cipher import AES

# ── CONFIG ────────────────────────────────────────────────
CRON_URL = os.environ.get(
    'CRON_URL',
    'https://lecturereminder.wuaze.com/class_reminder/cron_reminder.php'
    '?key=cr_d8d7ec068a4f9057cfef332cda54b710'
)

# ── LOGGING ───────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)
log = logging.getLogger()


def to_numbers(hex_str):
    """Convert hex string to list of ints."""
    return [int(hex_str[i:i+2], 16) for i in range(0, len(hex_str), 2)]


def to_hex(byte_list):
    """Convert list of ints to hex string."""
    return ''.join(f'{b:02x}' for b in byte_list)


def solve_aes_challenge(html):
    """
    InfinityFree serves this JS challenge:
        var a = toNumbers("..."), b = toNumbers("..."), c = toNumbers("...");
        document.cookie = "__test=" + toHex(slowAES.decrypt(c, 2, a, b)) + ...
    We replicate the AES-CBC decrypt in Python to get the cookie value.
    """
    pattern = (
        r'toNumbers\("([0-9a-f]+)"\).*?'   # a = key
        r'toNumbers\("([0-9a-f]+)"\).*?'   # b = iv
        r'toNumbers\("([0-9a-f]+)"\)'       # c = ciphertext
    )
    match = re.search(pattern, html, re.DOTALL)
    if not match:
        return None

    key        = bytes(to_numbers(match.group(1)))
    iv         = bytes(to_numbers(match.group(2)))
    ciphertext = bytes(to_numbers(match.group(3)))

    cipher    = AES.new(key, AES.MODE_CBC, iv)
    decrypted = cipher.decrypt(ciphertext)
    return to_hex(list(decrypted))


def run():
    session = requests.Session()
    session.headers.update({
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        )
    })

    log.info('Requesting cron URL...')
    resp = session.get(CRON_URL, timeout=30, allow_redirects=True)

    # Check if we hit the JS challenge
    if '__test' not in session.cookies and 'slowAES' in resp.text:
        log.info('JS challenge detected — solving AES cookie...')
        cookie_value = solve_aes_challenge(resp.text)

        if not cookie_value:
            log.error('Failed to parse AES challenge.')
            sys.exit(1)

        log.info(f'Cookie solved: __test={cookie_value[:8]}...')
        session.cookies.set('__test', cookie_value, domain='lecturereminder.wuaze.com')

        # Retry with the cookie
        resp = session.get(CRON_URL, timeout=30, allow_redirects=True)

    body = resp.text.strip()
    log.info(f'Response ({resp.status_code}): {body[:200]}')

    if resp.status_code == 200 and body == 'OK':
        log.info('Cron executed successfully.')
    elif 'slowAES' in resp.text:
        log.error('Still getting JS challenge after cookie solve — giving up.')
        sys.exit(1)
    else:
        log.warning(f'Unexpected response: {body[:500]}')


if __name__ == '__main__':
    run()
