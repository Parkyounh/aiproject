# -*- coding: utf-8 -*-
# 2_save_to_db_time.py (product_id 추가됨)

import os
import time  # time 모듈 추가
from PIL import Image
from weaviate.classes.data import DataObject
from utils import connect_to_weaviate, image_to_vector, WEAVIATE_CLASS_NAME

# -----------------------------------------------------------
# 1. 환경 설정
# -----------------------------------------------------------
MASKED_DIR = "images/product_craw_masked"  

masked_paths = [os.path.join(MASKED_DIR, f) for f in os.listdir(MASKED_DIR)
                 if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]

if len(masked_paths) == 0:
    print(f"❌ '{MASKED_DIR}' 폴더에 마스킹된 이미지가 없습니다! mask_and_save.py를 먼저 실행하세요.")
    exit()

# Weaviate 연결 및 컬렉션 가져오기
client = connect_to_weaviate()
collection = client.collections.get(WEAVIATE_CLASS_NAME)

data_objects_to_insert = []
print(f"\n🔄 {len(masked_paths)}개 이미지 벡터 생성 및 DB 전송 준비 중...")

# -----------------------------------------------------------
# 2. 벡터 생성 및 DataObject 리스트 구성 (시간 측정 추가 및 product_id 추출)
# -----------------------------------------------------------
total_start_time = time.time()  # 전체 시작 시간 기록

for path in masked_paths:
    start_time = time.time()  # 개별 파일 시작 시간 기록
    
    # 💡 파일명에서 product_id 추출 로직 추가
    filename = os.path.basename(path)
    # 20798351_1.jpg -> 20798351_1 (확장자 제거)
    base_name = os.path.splitext(filename)[0]
    # 20798351_1 -> 20798351 (마지막 '_숫자' 패턴 제거)
    try:
        # 파일명에서 마지막 '_숫자'를 제거하고 숫자로 변환합니다. (예: 20798351)
        # 만약 파일명이 '20798351.jpg' 형태만 있다면 os.path.splitext(filename)[0] 자체가 ID입니다.
        if '_' in base_name:
            product_id_str = base_name.rsplit('_', 1)[0]
        else:
            product_id_str = base_name

        # Weaviate 속성(properties)에 저장할 때 문자열 또는 정수로 변환 가능
        product_id = int(product_id_str)
        
    except ValueError:
        print(f"⚠️ WARNING: '{filename}'에서 product_id 추출 또는 숫자로 변환 실패. 건너뜀.")
        continue
    
    try:
        input_image_pil = Image.open(path)
        
        # 벡터 생성 (이미 마스킹되었으므로 remove_bg=False)
        vector = image_to_vector(input_image_pil, remove_bg=False)
        
        end_time = time.time()  # 개별 파일 끝 시간 기록
        time_taken = end_time - start_time  # 소요 시간 계산
        
        if vector and len(vector) > 0:
            # 💡 product_id 속성을 추가하여 저장
            data_objects_to_insert.append(
                DataObject(
                    properties={
                        "imagePath": path, 
                        "product_id": product_id # 추출된 product_id 저장 (정수형)
                    }, 
                    vector=vector
                )
            )
            print(f"🔹 Processing: {filename}, ID:{product_id}, Vector OK (소요 시간: {time_taken:.4f}초)")
        else:
            print(f"❌ WARNING: Vector is EMPTY for {filename}. Skipping. (소요 시간: {time_taken:.4f}초)")
            continue
            
    except Exception as e:
        print(f"❌ 벡터 생성 오류 ({filename}): {e}")

# -----------------------------------------------------------
# 3. Weaviate에 일괄 삽입
# -----------------------------------------------------------
# (나머지 코드는 동일)
print(f"\n📦 Weaviate에 {len(data_objects_to_insert)}개 데이터 전송 중...")

# DB 삽입 시간 측정
db_insert_start_time = time.time()
try:
    collection.data.insert_many(data_objects_to_insert)
    db_insert_end_time = time.time()
    db_insert_time = db_insert_end_time - db_insert_start_time
    
    total_end_time = time.time() # 전체 끝 시간 기록
    total_time_taken = total_end_time - total_start_time # 전체 소요 시간 계산
    
    print(f"✅ All {len(data_objects_to_insert)} images processed and sent to Weaviate for indexing. (DB 전송 시간: {db_insert_time:.4f}초)")
    print("\n--- DB 전송 및 준비 완료 ---")
    print(f"✨ **전체 처리 시간 (벡터 생성 + DB 전송): {total_time_taken:.4f}초**")

except Exception as e:
    print(f"\n❌ Weaviate 삽입 최종 실패: {e}")

finally:
    client.close()
    print("👋 Weaviate 클라이언트 연결 종료.")