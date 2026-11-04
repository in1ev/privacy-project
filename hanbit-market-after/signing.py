import hashlib
import hmac
import os
import secrets
import threading
import time
from functools import wraps

from flask import request, jsonify, current_app

SECRET_ENV = "HANBIT_SYNC_SECRET"
MAX_SKEW_SECONDS = 300          # 요청 시각이 현재와 5분 넘게 차이 나면 거부
NONCE_RETENTION = MAX_SKEW_SECONDS * 2 + 10


def _load_secret():
    secret = os.environ.get(SECRET_ENV)
    if not secret or len(secret) < 32:
        raise RuntimeError(
            f"환경변수 {SECRET_ENV}가 없거나 너무 짧습니다(32자 이상). 서비스 간 서명 키 없이는 서버를 시작할 수 없습니다."
        )
    return secret.encode("utf-8")


# import 시점에 읽는다. 키가 없으면 서버가 즉시 중단된다.
_SECRET = _load_secret()


def _signing_string(timestamp, nonce, method, path, body):
    """서명 대상 문자열. 시각·1회용 번호·메서드·경로·본문 해시를 묶어 서명한다."""
    body_hash = hashlib.sha256(body).hexdigest()
    return f"{timestamp}\n{nonce}\n{method.upper()}\n{path}\n{body_hash}".encode("utf-8")


def _mac(timestamp, nonce, method, path, body):
    return hmac.new(_SECRET, _signing_string(timestamp, nonce, method, path, body), hashlib.sha256).hexdigest()


def sign(method, path, body=b""):
    """보내는 쪽: 요청에 붙일 서명 헤더를 만든다. body는 실제로 전송할 바이트와 같아야 한다."""
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    return {
        "X-Hanbit-Timestamp": timestamp,
        "X-Hanbit-Nonce": nonce,
        "X-Hanbit-Signature": _mac(timestamp, nonce, method, path, body),
    }


_seen_nonces = {}
_lock = threading.Lock()


def verify(headers, method, path, body):
    """받는 쪽: 서명을 검증한다. (통과 여부, 실패 사유)를 돌려준다."""
    timestamp = headers.get("X-Hanbit-Timestamp")
    nonce = headers.get("X-Hanbit-Nonce")
    signature = headers.get("X-Hanbit-Signature")
    if not (timestamp and nonce and signature):
        return False, "서명 헤더 누락"

    try:
        ts = int(timestamp)
    except ValueError:
        return False, "타임스탬프 형식 오류"
    if abs(time.time() - ts) > MAX_SKEW_SECONDS:
        return False, "타임스탬프가 허용 범위를 벗어남"

    expected = _mac(timestamp, nonce, method, path, body)
    if not hmac.compare_digest(expected, signature):       # 시간 차 공격을 막기 위한 상수 시간 비교
        return False, "서명 불일치"

    # 재전송 방지: 서명이 맞는 요청에 대해서만 nonce를 기록한다 (엉터리 요청으로 저장소를 채우지 못하게)
    now = time.time()
    with _lock:
        for old in [n for n, t in _seen_nonces.items() if now - t > NONCE_RETENTION]:
            del _seen_nonces[old]
        if nonce in _seen_nonces:
            return False, "이미 사용된 요청(재전송)"
        _seen_nonces[nonce] = now
    return True, ""


def require_signed_request(fn):
    """서명이 유효한 서버 간 요청만 통과시킨다. 실패 사유는 응답이 아니라 서버 로그에만 남긴다."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        ok, reason = verify(request.headers, request.method, request.path, request.get_data())
        if not ok:
            current_app.logger.warning("발신처 인증 실패: %s (IP %s, %s %s)",
                                       reason, request.remote_addr, request.method, request.path)
            return jsonify({"error": "발신처 인증 실패"}), 401
        return fn(*args, **kwargs)
    return wrapper