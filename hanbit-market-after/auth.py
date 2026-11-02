import datetime
import os
from functools import wraps

import jwt
from flask import request, jsonify, g

from models import db, Member

SECRET_ENV = "HANBIT_JWT_SECRET"
ALGORITHM = "HS256"
TOKEN_LIFETIME = datetime.timedelta(minutes=30)


def _load_secret():
    secret = os.environ.get(SECRET_ENV)
    if not secret or len(secret) < 32:
        raise RuntimeError(
            f"환경변수 {SECRET_ENV}가 없거나 너무 짧습니다(32자 이상). 서명 키 없이는 서버를 시작할 수 없습니다."
        )
    return secret


# import 시점에 읽는다. 키가 없으면 서버가 즉시 중단된다.
_SECRET = _load_secret()


def issue_token(member_id):
    """토큰에는 신원(sub)과 만료 시각만 담는다. 권한(role)은 매 요청마다 DB에서 확인한다."""
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {"sub": str(member_id), "iat": now, "exp": now + TOKEN_LIFETIME}
    return jwt.encode(payload, _SECRET, algorithm=ALGORITHM)


def _bearer_token():
    parts = request.headers.get("Authorization", "").split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


def require_auth(*roles):
    """
    로그인한 사용자만 통과시킨다. roles를 주면 해당 역할만 통과시킨다.
      @require_auth()          → 로그인한 누구나
      @require_auth('admin')   → 관리자만
    인증 실패는 401, 권한 부족은 403을 돌려준다.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = _bearer_token()
            if not token:
                return jsonify({"error": "인증이 필요합니다"}), 401
            try:
                claims = jwt.decode(
                    token, _SECRET,
                    algorithms=[ALGORITHM],                      # 알고리즘을 고정(alg=none 등 차단)
                    options={"require": ["exp", "iat", "sub"]},
                )
                member = db.session.get(Member, int(claims["sub"]))
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "토큰이 만료되었습니다"}), 401
            except (jwt.InvalidTokenError, ValueError):
                return jsonify({"error": "유효하지 않은 토큰입니다"}), 401

            # 존재하지 않거나 탈퇴한 계정의 토큰은 만료 전이라도 거부한다.
            if member is None or member.is_withdrawn:
                return jsonify({"error": "유효하지 않은 계정입니다"}), 401

            g.current_member = member
            g.current_member_id = member.id            # 접속기록에 계정이 남는다
            if roles and member.role not in roles:
                return jsonify({"error": "권한이 없습니다"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator