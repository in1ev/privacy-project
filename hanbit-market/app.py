from flask import Flask, request, jsonify
from models import db, Member, Order
from datetime import datetime
import os

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "market.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)


# --- 회원가입 ---
@app.route('/members', methods=['POST']) # 이 URL로 이런 방식(GET/POST)의 요청이 오면 아래 함수를 실행하라.
def create_member():
    data = request.get_json()

    new_member = Member(
        name=data['name'],
        phone=data['phone'],                  # [결함2] 암호화 없이 그대로 저장
        email=data['email'],
        password_hash=data['password'],       # 주의: 실제로는 해시 처리 필요(별도 이슈, 이번 5대 결함 범위 밖)
        address=data.get('address'),
        card_number=data.get('card_number'),  # [결함2] 카드번호 전체를 암호화 없이 그대로 저장
        role=data.get('role', 'user')
    )
    db.session.add(new_member)
    db.session.commit()

    # [결함4] 접속기록(access_logs)에 남기는 코드가 없음 — 누가 언제 가입했는지 기록 자체가 안 됨

    return jsonify(new_member.to_dict()), 201


# --- 회원 단건 조회 ---
@app.route('/members/<int:member_id>', methods=['GET'])
def get_member(member_id):
    # [결함1] 이 API를 호출하는 사람이 admin인지 user인지 전혀 확인하지 않음
    # 원래는 아래와 같은 체크가 있어야 함:
    #   if request_user.role != 'admin' and request_user.id != member_id:
    #       return jsonify({'error': '권한 없음'}), 403
    member = Member.query.get_or_404(member_id)
    return jsonify(member.to_dict())  # card_number, phone까지 필터링 없이 그대로 반환


# --- 전체 회원 목록 조회 (관리자용으로 의도했으나 실제로는 아무나 호출 가능) ---
@app.route('/admin/members', methods=['GET'])
def list_all_members():
    # [결함1] 여기가 결함 1이 가장 명확하게 드러나는 지점
    # role 체크가 전혀 없어서, "관리자 페이지"라는 이름만 붙었을 뿐
    # CS 담당자든 일반 유저든 이 URL을 알기만 하면 전체 회원의 카드번호까지 조회 가능
    members = Member.query.all()
    return jsonify([m.to_dict() for m in members])


# --- 회원 탈퇴 ---
@app.route('/members/<int:member_id>/withdraw', methods=['POST'])
def withdraw_member(member_id):
    member = Member.query.get_or_404(member_id)

    # [결함7] 탈퇴 "표시"만 하고 개인정보 값은 전혀 지우지 않음
    member.is_withdrawn = True
    member.withdrawn_at = datetime.utcnow()
    # 원래는 아래와 같은 익명화 처리가 필요함:
    #   member.name = "탈퇴회원"
    #   member.phone = None
    #   member.card_number = None
    #   member.address = None

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
        db.create_all()   # models.py의 설계도대로 실제 market.db 파일과 테이블을 생성. 이 파일 실행 시 models.py의 설계도가 실제 market.db 파일로 변환
    app.run(debug=True, port=5000)