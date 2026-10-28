from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class PayAccount(db.Model):
    __tablename__ = 'pay_accounts'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)           # [결함2] 평문 저장 (한빛마켓과 동일 결함 패턴)
    birth_date = db.Column(db.String(10))                        # 생년월일 (실명확인정보 일부)
    linked_market_id = db.Column(db.Integer, nullable=True)      # 한빛마켓 회원 id 참조 (연동 시)

    balance = db.Column(db.Integer, default=0)                   # 잔액(원)
    bank_account = db.Column(db.String(30))                      # [결함2] 계좌번호 평문 저장

    role = db.Column(db.String(20), default='user')              # [결함1] 동일한 패턴의 접근권한 결함

    is_withdrawn = db.Column(db.Boolean, default=False)
    withdrawn_at = db.Column(db.DateTime, nullable=True)          # [결함7] 동일 패턴

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'birth_date': self.birth_date,
            'linked_market_id': self.linked_market_id,
            'balance': self.balance,
            'bank_account': self.bank_account,
            'role': self.role,
            'is_withdrawn': self.is_withdrawn,
            'withdrawn_at': self.withdrawn_at.isoformat() if self.withdrawn_at else None,
            'created_at': self.created_at.isoformat()
        }


class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('pay_accounts.id'), nullable=False)
    type = db.Column(db.String(20))          # 충전 / 결제 / 송금
    amount = db.Column(db.Integer, nullable=False)
    counterparty = db.Column(db.String(100))  # 거래 상대방(가맹점명 등)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'account_id': self.account_id,
            'type': self.type,
            'amount': self.amount,
            'counterparty': self.counterparty,
            'created_at': self.created_at.isoformat()
        }

# [결함4] 여기도 access_logs 테이블이 없음 — 한빛마켓과 동일한 결함 패턴 반복