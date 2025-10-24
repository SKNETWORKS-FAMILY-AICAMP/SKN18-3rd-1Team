import re

"""
📘 파일별 정규식 패턴 정의 (공통 편/장/절/조 인식)
──────────────────────────────────────────────
"""
# ==========================================================
# 1️⃣ 공통 패턴 정의
# ==========================================================
COMMON_PATTERNS = {
    "name": "공통 편장절조 구조",
    "part": r"^\s*제\s*\d+\s*편\s*[^\n]+",
    "chapter": r"^\s*제\s*\d+\s*장\s*[^\n]+",
    "section": r"^\s*제\s*\d+\s*절\s*[^\n]+",
    "article": r"^\s*제\s*\d+\s*조\s*(\([^)]+\))?\s*[^\n]*",
    "appendix_title": r"^\s*\[별표\s*\d+\]\s*[^\n]*",
    "appendix_item": r"^\s*(\[부칙\]|\[참고\]|\[예시\])\s*[^\n]*",
    "skip_patterns": [
        r"QR\s*코드", r"목차", r"=+\s*목\s*차\s*=+",
        r"이\s*약관은\s*보험소비자", r"보험소비자의\s*권익\s*보호",
        r"확인필\s*[-–]", r"인가", r"금융감독원"
    ],
    "content_start_patterns": [
        r"제\s*1\s*편",
        r"제\s*1\s*장",
        r"제\s*1\s*조"
    ]
}

# ==========================================================
# 2️⃣ 패턴 선택 함수
# ==========================================================
def get_patterns_by_filename(filename: str) -> dict:
    """파일명에 상관없이 공통 패턴 반환"""
    return COMMON_PATTERNS

# ==========================================================
# 3️⃣ 유틸 함수
# ==========================================================
def detect_content_start(text: str, patterns: dict) -> int:
    """본문 시작 위치 감지 (제1편/제1장/제1조)"""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        for start_pattern in patterns.get("content_start_patterns", []):
            if re.search(start_pattern, line):
                print(f"⚙️ 본문 시작 감지: '{line.strip()}' (line {i})")
                return i
    return 0

def should_skip_line(line: str, patterns: dict) -> bool:
    """불필요한 라인 제외"""
    for skip_pattern in patterns.get("skip_patterns", []):
        if re.search(skip_pattern, line):
            return True
    return False
