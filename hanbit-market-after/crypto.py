import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_ENV = "HANBIT_DATA_KEY"
PREFIX = "enc:v1:"          # 암호문 표지(버전 포함). 평문과 구분하는 용도


def _load_key():
    raw = os.environ.get(KEY_ENV)
    if not raw:
        raise RuntimeError(
            f"환경변수 {KEY_ENV}가 설정되지 않았습니다. 암호화 키 없이는 서버를 시작할 수 없습니다."
        )
    key = base64.urlsafe_b64decode(raw)
    if len(key) != 32:
        raise RuntimeError(f"{KEY_ENV}는 32바이트 키를 base64로 인코딩한 값이어야 합니다.")
    return key


# import 시점에 키를 읽는다. 키가 없으면 서버가 즉시 중단된다(평문 저장으로 조용히 넘어가지 않음).
_aesgcm = AESGCM(_load_key())


def encrypt(plaintext):
    """AES-256-GCM으로 암호화한다. 값마다 새 nonce(12바이트)를 쓴다."""
    if plaintext is None:
        return None
    nonce = os.urandom(12)
    ciphertext = _aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return PREFIX + base64.urlsafe_b64encode(nonce + ciphertext).decode("ascii")


def decrypt(token):
    if token is None:
        return None
    if not token.startswith(PREFIX):
        raise ValueError("암호문 형식이 아닙니다 (평문이 저장되어 있을 수 있음)")
    raw = base64.urlsafe_b64decode(token[len(PREFIX):])
    nonce, ciphertext = raw[:12], raw[12:]
    return _aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")


def mask_phone(phone):
    if not phone or len(phone) < 8:
        return "****"
    return f"{phone[:3]}-****-{phone[-4:]}"


def mask_card(card):
    if not card or len(card) <= 4:
        return "****"
    return "*" * (len(card) - 4) + card[-4:]