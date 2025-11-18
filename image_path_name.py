import re
import json
import pandas as pd
import csv

# -----------------------------
# 1) 값 정리 및 파싱 함수 (JSON 변환용)
# -----------------------------
def clean_value(v):
    v = v.strip()
    v = re.sub(r'^[\(\[]+', '', v)
    v = re.sub(r'[\)\]]+$', '', v)
    return v.strip()

def parse_value(v):
    v = clean_value(v)
    if ',' in v:
        return [item.strip() for item in v.split(',') if item.strip()]
    date = re.search(r'(\d{4})년\s*(\d{1,2})월(?:\s*(\d{1,2})일)?', v)
    if date:
        y = int(date.group(1)); m = int(date.group(2)); d = date.group(3)
        if d: return f"{y:04d}-{m:02d}-{int(d):02d}"
        return f"{y:04d}-{m:02d}"
    return v

def parse_text(text):
    result = {}
    if not isinstance(text, str): return result
    text = text.replace("(/", "/").replace(" (/", "/").replace("/(", "/")
    items = [p for p in text.split('/') if p.strip()]
    for item in items:
        if ':' in item:
            key, val = item.split(':', 1)
            result[key.strip()] = parse_value(val)
    return result

# -----------------------------
# 4) CSV 읽고, 변환, 삭제, 이미지 URL 정리 후 저장 (통합)
# -----------------------------
input_file = "danawa_유모차_output_with_pcode (2).csv"
output_file = "danawa_유모차_output_final_cleaned_img_modified.csv" 

# 1. CSV 읽기
df = pd.read_csv(input_file, encoding="utf-8-sig")

# 2. 이미지 URL에서 파일 이름 추출 및 형식 수정 (수정된 부분)
print("이미지 URL에서 파일 이름 추출 및 정리 중...")

# 2-1. URL에서 파일 이름 추출 (예: 'https://.../20834387_1.jpg?...' -> '20834387_1.jpg')
df['상품이미지'] = df['상품이미지'].astype(str).str.extract(r'([^/]+\.(?:jpg|png))')

# 2-2. 파일 이름에서 '_숫자' 부분 제거 (예: '20834387_1.jpg' -> '20834387.jpg')
# _ 뒤에 숫자가 오고, 그 뒤에 .jpg나 .png가 오는 패턴을 찾아서 '_숫자'를 제거합니다.
df['상품이미지'] = df['상품이미지'].str.replace(r'_\d+(?=\.(?:jpg|png)$)', '', regex=True)


# 3. '상세정보_json' 열 생성 및 원본 '상세정보' 열 삭제
print("상세정보 JSON 변환 및 원본 열 삭제 중...")
df["상세정보_json"] = df["상세정보"].astype(str).apply(
    lambda x: json.dumps(parse_text(x), ensure_ascii=False)
)
df = df.drop(columns=['상세정보'])

# 4. CSV 저장 (깨짐 방지 옵션 적용)
df.to_csv(
    output_file, 
    index=False, 
    encoding="utf-8-sig", 
    sep=',', 
    quoting=csv.QUOTE_ALL
)

print(f"✅ 모든 변환 및 정리 완료: {output_file}")