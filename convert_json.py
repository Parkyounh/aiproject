import re
import json
import pandas as pd
import csv # QUOTING 옵션 사용을 위해 추가

# -----------------------------
# 1) 값 정리(괄호 제거 등)
# -----------------------------
def clean_value(v):
    v = v.strip()
    # 앞뒤 괄호 제거
    v = re.sub(r'^[\(\[]+', '', v)
    v = re.sub(r'[\)\]]+$', '', v)
    return v.strip()


# -----------------------------
# 2) 값 파싱(JSON 변환용)
# -----------------------------
def parse_value(v):
    v = clean_value(v)

    # 콤마 → 리스트
    if ',' in v:
        return [item.strip() for item in v.split(',') if item.strip()]

    # 날짜 → YYYY-MM(-DD)
    date = re.search(r'(\d{4})년\s*(\d{1,2})월(?:\s*(\d{1,2})일)?', v)
    if date:
        y = int(date.group(1))
        m = int(date.group(2))
        d = date.group(3)
        if d:
            return f"{y:04d}-{m:02d}-{int(d):02d}"
        return f"{y:04d}-{m:02d}"

    return v


# -----------------------------
# 3) 상세정보 문자열 → JSON 변환
# -----------------------------
def parse_text(text):
    result = {}

    if not isinstance(text, str):
        return result

    # "/(" 또는 " (/" 같은 패턴 정리
    text = text.replace("(/", "/")
    text = text.replace(" (/", "/")
    text = text.replace("/(", "/")

    items = [p for p in text.split('/') if p.strip()]

    for item in items:
        if ':' in item:
            key, val = item.split(':', 1)
            key = key.strip()
            result[key] = parse_value(val)

    return result


# -----------------------------
# 4) CSV 읽고, 변환, 삭제, 저장 (통합)
# -----------------------------
input_file = "danawa_유모차_output_with_pcode (2).csv"
output_file = "danawa_유모차_output_final_cleaned.csv" # 최종 결과 파일명

# 1. CSV 읽기 (한글 깨짐 방지)
df = pd.read_csv(input_file, encoding="utf-8-sig")

# 2. '상세정보_json' 열 생성
print("상세정보 JSON 변환 중...")
df["상세정보_json"] = df["상세정보"].astype(str).apply(
    lambda x: json.dumps(parse_text(x), ensure_ascii=False)
)

# 3. 원본 '상세정보' 열 즉시 삭제
print("원본 상세정보 열 삭제 중...")
df = df.drop(columns=['상세정보'])

# 4. CSV 저장 (깨짐 방지 옵션 적용)
# sep=',': 쉼표 구분자 사용
# quoting=csv.QUOTE_ALL: JSON 문자열 내 쉼표 때문에 행이 나뉘는 것을 방지
df.to_csv(
    output_file, 
    index=False, 
    encoding="utf-8-sig", 
    sep=',', 
    quoting=csv.QUOTE_ALL
)

print(f"✅ 변환, 삭제 및 저장 완료: {output_file}")