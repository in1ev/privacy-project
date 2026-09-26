from flask import Flask, request, jsonify
from models import db, PayAccount, Transaction
from datetime import datetime
import os

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "pay.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# --- 계정 연동/생성 (한빛마켓 → 한빛페이 데이터 이전 지점) ---
@app.route('/accounts/link', methods=['POST'])
def link_account():
    data = request.get_json()

    # [결함6] 한빛마켓에서 넘어온 이 요청이
    #         제대로 된 제3자 제공 동의를 거쳤는지 여기서는 전혀 검증하지 않음
    #         (요청이 오면 그냥 그대로 신뢰하고 계정을 생성)
    new_account = PayAccount(
        name=data['name'],
        phone=data['phone'],
        birth_date=data.get('birth_date'),
        linked_market_id=data.get('market_id'),
        bank_account=data.get('bank_account'),
        role=data.get('role', 'user')
    )
    db.session.add(new_account)
    db.session.commit()

    return jsonify(new_account.to_dict()), 201


# --- 계정 단건 조회 ---
@app.route('/accounts/<int:account_id>', methods=['GET'])
def get_account(account_id):
    # [결함1] 동일하게 권한 체크 없음
    account = PayAccount.query.get_or_404(account_id)
    return jsonify(account.to_dict())


# --- 결제 처리 ---
@app.route('/accounts/<int:account_id>/pay', methods=['POST'])
def process_payment(account_id):
    account = PayAccount.query.get_or_404(account_id)
    data = request.get_json()
    amount = data['amount']

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
def charge_account(account_id):
    account = PayAccount.query.get_or_404(account_id)
    data = request.get_json()
    amount = data['amount']

    account.balance += amount
    new_tx = Transaction(account_id=account_id, type='충전', amount=amount)
    db.session.add(new_tx)
    db.session.commit()

    return jsonify({'message': '충전 완료', 'account': account.to_dict()})


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5001)   # 한빛마켓(5000)과 겹치지 않게 포트를 5001로 지정