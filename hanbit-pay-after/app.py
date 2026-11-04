from flask import Flask, request, jsonify
from models import db, PayAccount, Transaction
from signing import require_signed_request
import os

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "pay.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


def _valid_amount(value):
    """금액은 1 이상의 정수만 허용한다. (음수 결제로 잔액이 늘어나는 오류 방지)"""
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


# 이 서비스의 모든 API는 서비스 간 호출 전용으로 보고, 서명된 요청만 받는다.
# (한빛페이 최종 사용자 로그인은 이번 프로토타입 범위 밖)

# --- 계정 연동 (한빛마켓 → 한빛페이) ---
@app.route('/accounts/link', methods=['POST'])
@require_signed_request          # [개선3] 요청이 한빛마켓에서 온 것인지 서명으로 검증
def link_account():
    data = request.get_json(silent=True) or {}

    if not data.get('name') or not data.get('phone') or not isinstance(data.get('market_id'), int):
        return jsonify({'error': '필수 항목 누락 또는 형식 오류 (name, phone, market_id)'}), 400
    if PayAccount.query.filter_by(linked_market_id=data['market_id']).first():
        return jsonify({'error': '이미 연동된 회원입니다'}), 409

    new_account = PayAccount(
        name=data['name'],
        phone=data['phone'],
        birth_date=data.get('birth_date'),
        linked_market_id=data['market_id'],
        bank_account=data.get('bank_account'),
        role='user'              # [개선3] 요청이 보낸 role은 무시한다
    )
    db.session.add(new_account)
    db.session.commit()

    return jsonify(new_account.to_dict()), 201


# --- 계정 단건 조회 ---
@app.route('/accounts/<int:account_id>', methods=['GET'])
@require_signed_request
def get_account(account_id):
    account = PayAccount.query.get_or_404(account_id)
    return jsonify(account.to_dict())


# --- 결제 처리 ---
@app.route('/accounts/<int:account_id>/pay', methods=['POST'])
@require_signed_request
def process_payment(account_id):
    account = PayAccount.query.get_or_404(account_id)
    data = request.get_json(silent=True) or {}
    amount = data.get('amount')
    if not _valid_amount(amount):
        return jsonify({'error': '금액은 1 이상의 정수여야 합니다'}), 400

    if account.balance < amount:
        return jsonify({'error': '잔액 부족'}), 400

    account.balance -= amount
    new_tx = Transaction(
        account_id=account_id,
        type='결제',
        amount=amount,
        counterparty=data.get('counterparty', '한빛마켓')
    )
    db.session.add(new_tx)
    db.session.commit()

    return jsonify({'message': '결제 완료', 'account': account.to_dict(), 'transaction': new_tx.to_dict()})


# --- 충전 ---
@app.route('/accounts/<int:account_id>/charge', methods=['POST'])
@require_signed_request
def charge_account(account_id):
    account = PayAccount.query.get_or_404(account_id)
    data = request.get_json(silent=True) or {}
    amount = data.get('amount')
    if not _valid_amount(amount):
        return jsonify({'error': '금액은 1 이상의 정수여야 합니다'}), 400

    account.balance += amount
    new_tx = Transaction(account_id=account_id, type='충전', amount=amount)
    db.session.add(new_tx)
    db.session.commit()

    return jsonify({'message': '충전 완료', 'account': account.to_dict()})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=False, port=5011)      # [개선3] 디버그 모드를 끈다