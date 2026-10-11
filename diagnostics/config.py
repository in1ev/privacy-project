import os
from dataclasses import dataclass

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


@dataclass
class Target:
    name: str
    market_url: str
    pay_url: str
    market_db_path: str


# 기본 대상 (현재 로컬 환경)
DEFAULT_TARGET = Target(
    name="local",
    market_url="http://127.0.0.1:5000",
    pay_url="http://127.0.0.1:5001",
    market_db_path=os.path.join(BASE_DIR, 'hanbit-market', 'market.db'),
)