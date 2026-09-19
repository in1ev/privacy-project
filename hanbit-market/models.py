from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
# DB를 작성하기 위한 설계도. 이 파일 자체로는 DB가 만들어지진 않음
db = SQLAlchemy()


class Member(db.Model):
    __tablename__ = 'members'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)          # [결함2] 평문 저장
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300))
    card_number = db.Column(db.String(20))                    # [결함2] 카드번호 전체 평문 저장

    role = db.Column(db.String(20), default='user')           # [결함1] admin/cs/user 구분은 있으나
                                                                #          이 값을 체크하는 로직이 API 단에 없음

    is_withdrawn = db.Column(db.Boolean, default=False)
    withdrawn_at = db.Column(db.DateTime, nullable=True)       # [결함7] 탈퇴 시각만 기록, 개인정보는 그대로 잔존

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        # 주의: Before 버전에서는 role 구분 없이 이 메서드가 모든 필드를 그대로 반환함 (결함1의 실제 발현 지점)
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'email': self.email,
            'address': self.address,
            'card_number': self.card_number,
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


# [결함4] access_logs 테이블이 Before 버전에는 존재하지 않음 (의도적 누락)
# → After 버전에서 아래와 같은 테이블을 추가할 예정:
#
# class AccessLog(db.Model):
#     __tablename__ = 'access_logs'
#     id = db.Column(db.Integer, primary_key=True)
#     member_id = db.Column(db.Integer, db.ForeignKey('members.id'))
#     action = db.Column(db.String(100))
#     target_id = db.Column(db.Integer)
#     ip_address = db.Column(db.String(50))
#     timestamp = db.Column(db.DateTime, default=datetime.utcnow)