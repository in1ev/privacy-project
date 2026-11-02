"""
상담원(cs)·관리자(admin) 계정을 만든다. API가 아니라 서버 PC에서만 실행할 수 있다.
사용법:  python create_staff.py admin admin@hanbit.test "관리자"
"""
import getpass
import sys

from werkzeug.security import generate_password_hash

from app import app
from models import db, Member
from crypto import encrypt


def create_staff(role, email, name, password):
    if role not in ('admin', 'cs'):
        raise ValueError("role은 admin 또는 cs여야 합니다")
    if len(password) < 8:
        raise ValueError("비밀번호는 8자 이상이어야 합니다")
    email = email.strip().lower()
    with app.app_context():
        db.create_all()
        if Member.query.filter_by(email=email).first():
            raise ValueError("이미 존재하는 이메일입니다")
        db.session.add(Member(
            name=name,
            phone=encrypt("00000000000"),     # 직원 계정용 자리표시 번호
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
        ))
        db.session.commit()


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print('사용법: python create_staff.py <admin|cs> <이메일> "<이름>"')
        sys.exit(1)
    try:
        create_staff(sys.argv[1], sys.argv[2], sys.argv[3], getpass.getpass("비밀번호(8자 이상): "))
    except ValueError as e:
        print("실패:", e)
        sys.exit(1)
    print(f"{sys.argv[1]} 계정을 만들었습니다: {sys.argv[2]}")