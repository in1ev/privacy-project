from flask import Flask, request, jsonify
from models import db, Member, Order
from crypto import encrypt
from datetime import datetime
import os

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "market.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# --- 회원가입 ---
@app.route('/members', methods=['POST'])
def create_member():
    data = request.get_json()

    new_member = Member(
        name=data['name'],
        phone=encrypt(data['phone']),                  # [개선2] 저장 전에 암호화
        email=data['email'],
        password_hash=data['password'],                # 주의: 해시 처리는 결함1 단계에서 함께 개선 예정
        address=data.get('address'),
        card_number=encrypt(data.get('card_number')),  # [개선2] 저장 전에 암호화
        role=data.get('role', 'user')
    )
    db.session.add(new_member)
    db.session.commit()

    # [결함4] 접속기록(access_logs)에 남기는 코드가 없음

    return jsonify(new_member.to_dict()), 201


# --- 회원 단건 조회 ---
@app.route('/members/<int:member_id>', methods=['GET'])
def get_member(member_id):
    # [결함1] 이 API를 호출하는 사람이 누구인지 확인하지 않음
    member = Member.query.get_or_404(member_id)
    return jsonify(member.to_dict())


# --- 전체 회원 목록 조회 (관리자용으로 의도했으나 실제로는 아무나 호출 가능) ---
@app.route('/admin/members', methods=['GET'])
def list_all_members():
    # [결함1] role 체크가 전혀 없음
    members = Member.query.all()
    return jsonify([m.to_dict() for m in members])


# --- 회원 탈퇴 ---
@app.route('/members/<int:member_id>/withdraw', methods=['POST'])
def withdraw_member(member_id):
    member = Member.query.get_or_404(member_id)

    # [결함7] 탈퇴 "표시"만 하고 개인정보 값은 지우지 않음
    member.is_withdrawn = True
    member.withdrawn_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'message': '탈퇴 처리 완료', 'member': member.to_dict()})


# --- 주문 생성 ---
@app.route('/orders', methods=['POST'])
def create_order():
    data = request.get_json()
    new_order = Order(
        member_id=data['member_id'],
        product_name=data['product_name'],
        amount=data['amount']
    )
    db.session.add(new_order)
    db.session.commit()
    return jsonify(new_order.to_dict()), 201


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, port=5010)