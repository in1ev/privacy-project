import os
from dataclasses import dataclass

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


@dataclass
class Target:
    name: str
    market_url: str
    pay_url: str
    market_db_path: str
    env_path: str = os.path.join(BASE_DIR, 'venv')   # 패치 점검 대상 가상환경


BEFORE_TARGET = Target(
    name="Before",
    market_url="http://127.0.0.1:5000",
    pay_url="http://127.0.0.1:5001",
    market_db_path=os.path.join(BASE_DIR, 'hanbit-market', 'market.db'),
    env_path=os.path.join(BASE_DIR, 'venv'),
)

AFTER_TARGET = Target(
    name="After",
    market_url="http://127.0.0.1:5010",
    pay_url="http://127.0.0.1:5011",
    market_db_path=os.path.join(BASE_DIR, 'hanbit-market-after', 'market.db'),
    env_path=os.path.join(BASE_DIR, 'venv_after'),
)

DEFAULT_TARGET = BEFORE_TARGET