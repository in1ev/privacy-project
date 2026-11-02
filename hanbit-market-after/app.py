from flask import Flask, request, jsonify, g
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, Member, Order, AccessLog
from auth import require_auth, issue_token, TOKEN_LIFETIME
from crypto import encrypt
from datetime import datetime
import os

app = Flask(__name__)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(basedir, "market.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

# 존재하지 않는 이메일로 로그인해도 비밀번호 검증과 비슷한 시간이 걸리게 하기 위한 더미 해시
DUMMY_HASH = generate_password_hash("dummy-password-for-timing")


# --- 접속기록 (모든 요청 공통) ---
@app.after_request
def write_access_log(response):
    """
    [개선4] 모든 요청의 처리 결과를 access_logs에 남긴다.
    - 요청 본문과 쿼리 값은 기록하지 않는다 (개인정보가 로그에 남지 않도록).
    - 로그 저장이 실패해도 원래 응답은 그대로 돌려주되, 실패 사실은 서버 로그에 남긴다.
    """
    try:
        db.session.rollback()    # 요청 처리 중 실패한 트랜잭션이 남아 있으면 먼저 정리
        rule = request.url_rule.rule if request.url_rule else "(no route)"
        view_args = request.view_args or {}
        db.session.add(AccessLog(
            member_id=getattr(g, "current_member_id", None),   # 로그인한 요청이면 계정이 남는다
            action=f"{request.method} {rule}",
            target_id=view_args.get("member_id"),
            ip_address=request.remote_addr,
            status_code=response.status_code,
        ))
        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("접속기록 저장 실패")
    return response


# --- 회원가입 (인증 불필요) ---
@app.route('/members', methods=['POST'])
def create_member():
    data = request.get_json(silent=True) or {}

    missing = [k for k in ('name', 'phone', 'email', 'password') if not data.get(k)]
    if missing:
        return jsonify({'error': f"필수 항목 누락: {', '.join(missing)}"}), 400
    if len(str(data['password'])) < 8:
        return jsonify({'error': '비밀번호는 8자 이상이어야 합니다'}), 400

    email = str(data['email']).strip().lower()
    if Member.query.filter_by(email=email).first():
        return jsonify({'error': '이미 가입된 이메일입니다'}), 409

    new_member = Member(
        name=data['name'],
        phone=encrypt(str(data['phone'])),                       # [개선2] 저장 전에 암호화
        email=email,
        password_hash=generate_password_hash(str(data['password'])),   # [개선1] 비밀번호는 해시로만 저장
        address=data.get('address'),
        card_number=encrypt(data.get('card_number')),            # [개선2] 저장 전에 암호화
        role='user'        # [개선1] 가입 시 권한은 항상 일반 사용자. 클라이언트가 보낸 role은 무시한다
    )
    db.session.add(new_member)
    try:
        db.session.commit()
    except IntegrityError:           # 동시 가입 등으로 이메일이 겹친 경우
        db.session.rollback()
        return jsonify({'error': '이미 가입된 이메일입니다'}), 409

    return jsonify(new_member.to_dict()), 201


# --- 로그인 ---
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', ''))

    member = Member.query.filter_by(email=email).first()
    # 이메일이 없어도 해시 검증을 수행해, 응답 시간으로 가입 여부를 알아내기 어렵게 한다
    password_ok = check_password_hash(member.password_hash if member else DUMMY_HASH, password)

    # 이메일 없음/비밀번호 오류/탈퇴 계정을 같은 응답으로 처리한다
    if not (member and password_ok and not member.is_withdrawn):
        return jsonify({'error': '이메일 또는 비밀번호가 올바르지 않습니다'}), 401

    g.current_member_id = member.id      # 로그인 성공도 접속기록에 계정이 남는다
    return jsonify({
        'access_token': issue_token(member.id),
        'token_type': 'Bearer',
        'expires_in': int(TOKEN_LIFETIME.total_seconds()),
    })


# --- 회원 단건 조회: 본인, 상담원, 관리자만 ---
@app.route('/members/<int:member_id>', methods=['GET'])
@require_auth()
def get_member(member_id):
    me = g.current_member
    # [개선1] 일반 사용자는 본인 정보만. 존재 여부와 상관없이 같은 403을 돌려줘 회원 id 추측을 막는다
    if me.role == 'user' and me.id != member_id:
        return jsonify({'error': '권한이 없습니다'}), 403
    member = db.get_or_404(Member, member_id)
    return jsonify(member.to_dict(for_role=me.role))


# --- 전체 회원 목록 조회: 관리자만 ---
@app.route('/admin/members', methods=['GET'])
@require_auth('admin')            # [개선1] 이름만 관리자용이 아니라 실제로 관리자만 통과
def list_all_members():
    members = Member.query.all()
    return jsonify([m.to_dict(for_role='admin') for m in members])


# --- 회원 탈퇴: 본인 또는 관리자만 ---
@app.route('/members/<int:member_id>/withdraw', methods=['POST'])
@require_auth()
def withdraw_member(member_id):
    me = g.current_member
    if me.id != member_id and me.role != 'admin':
        return jsonify({'error': '권한이 없습니다'}), 403
    member = db.get_or_404(Member, member_id)

    # [결함7] 탈퇴 "표시"만 하고 개인정보 값은 지우지 않음
    member.is_withdrawn = True
    member.withdrawn_at = datetime.utcnow()

    db.session.commit()
    return jsonify({'message': '탈퇴 처리 완료', 'member': member.to_dict(for_role=me.role)})


# --- 주문 생성: 본인 주문만 ---
@app.route('/orders', methods=['POST'])
@require_auth()
def create_order():
    data = request.get_json(silent=True) or {}
    missing = [k for k in ('member_id', 'product_name', 'amount') if data.get(k) is None]
    if missing:
        return jsonify({'error': f"필수 항목 누락: {', '.join(missing)}"}), 400
    if data['member_id'] != g.current_member.id:    # [개선1] 다른 사람 명의로 주문 생성 차단
        return jsonify({'error': '권한이 없습니다'}), 403

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
    # [개선1] 디버그 모드를 끈다. 디버그 모드는 오류 화면에 SQL 파라미터(전화번호·카드번호 등)를
    #         그대로 보여 주고, 대화형 디버거까지 열어 둔다.
    app.run(debug=False, port=5010)