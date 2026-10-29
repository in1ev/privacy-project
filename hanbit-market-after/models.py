from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

from crypto import decrypt, mask_phone, mask_card

db = SQLAlchemy()


def _view(token, masker):
    """저장된 암호문을 복호화한 뒤 마스킹해서 돌려준다."""
    if token is None:
        return None
    try:
        return masker(decrypt(token))
    except Exception:
        return "[복호화 실패]"


class Member(db.Model):
    __tablename__ = 'members'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(255), nullable=False)         # [개선2] AES-GCM 암호문 저장
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300))
    card_number = db.Column(db.String(255))                   # [개선2] AES-GCM 암호문 저장

    role = db.Column(db.String(20), default='user')           # [결함1] admin/cs/user 구분은 있으나
                                                                #          이 값을 체크하는 로직이 API 단에 없음

    is_withdrawn = db.Column(db.Boolean, default=False)
    withdrawn_at = db.Column(db.DateTime, nullable=True)       # [결함7] 탈퇴 시각만 기록, 개인정보는 그대로 잔존

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        # 응답에는 암호문이 아니라 마스킹된 값만 나간다.
        # (결함1은 아직 남아 있어 role 구분 없이 누구나 이 응답을 받을 수 있음)
        return {
            'id': self.id,
            'name': self.name,
            'phone': _view(self.phone, mask_phone),
            'email': self.email,
            'address': self.address,
            'card_number': _view(self.card_number, mask_card),
            'role': self.role,
            'is_withdrawn': self.is_withdrawn,
            'withdrawn_at': self.withdrawn_at.isoformat() if self.withdrawn_at else None,
            'created_at': self.created_at.isoformat()
        }


class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, db.ForeignKey('members.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(50), default='결제완료')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'member_id': self.member_id,
            'product_name': self.product_name,
            'amount': self.amount,
            'status': self.status,
            'created_at': self.created_at.isoformat()
        }

class AccessLog(db.Model):
    """
    접속기록. 개인정보 처리 시스템에 누가·언제·어디서·무엇을 했는지 남긴다.
    (계정, 접속일시, 접속지 정보, 처리한 정보주체, 수행업무)
    요청 본문(이름·전화번호·카드번호 등)은 개인정보가 들어 있으므로 기록하지 않는다.
    """
    __tablename__ = 'access_logs'

    id = db.Column(db.Integer, primary_key=True)
    member_id = db.Column(db.Integer, nullable=True)       # 요청한 계정 (로그인 도입 전에는 비어 있음)
    action = db.Column(db.String(200), nullable=False)     # 수행업무: "메서드 + 경로 규칙"
    target_id = db.Column(db.Integer, nullable=True)       # 처리한 정보주체(회원) id
    ip_address = db.Column(db.String(50))                  # 접속지 정보
    status_code = db.Column(db.Integer)                    # 처리 결과 (200, 401, 404 ...)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)   # 접속일시 (UTC)