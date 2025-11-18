# mysql_similarity_search.py
# MySQL에 저장된 벡터를 불러와 Python에서 유사도를 계산하고 시간을 측정합니다.

import sys
import time
import json
import numpy as np
import mysql.connector
from operator import itemgetter

# -----------------------------------------------------------
# 1. 설정값 (사용자 입력)
# -----------------------------------------------------------
# 🔍 쿼리할 대상의 product_id를 여기에 입력 (숫자)
QUERY_PRODUCT_ID = 20787518
# 📊 결과를 몇 개까지 보여줄지 설정
QUERY_LIMIT = 5
TABLE_NAME = "product_vectors" 

# -----------------------------------------------------------
# 2. MySQL 연결 설정
# (weaviate_to_mysql.py에서 사용한 설정과 동일)
# -----------------------------------------------------------
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'aiproject',
    'port': 3305 
}

# -----------------------------------------------------------
# 3. 코사인 유사도 계산 함수
# -----------------------------------------------------------
def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """두 벡터의 코사인 유사도를 계산합니다."""
    # 분자: 내적 (Dot Product)
    dot_product = np.dot(vec_a, vec_b)
    # 분모: 각 벡터의 L2 노름 (Euclidean Norm)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)

# -----------------------------------------------------------
# 4. MySQL 연결 및 데이터 조회
# -----------------------------------------------------------
def run_mysql_similarity_search():
    print(f"\n🔄 MySQL 유사도 검색 시작 (쿼리 ID: {QUERY_PRODUCT_ID}, Limit: {QUERY_LIMIT})")
    
    # 📌 1단계: 전체 데이터 로드 시간 측정 시작
    total_start_time = time.time()
    
    try:
        mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
        mysql_cursor = mysql_conn.cursor()
    except mysql.connector.Error as err:
        print(f"❌ MySQL 연결 실패: {err}")
        return

    query_vector = None
    all_vectors = []
    
    # -----------------------------------------------------------
    # 4-1. 모든 벡터 데이터 및 쿼리 대상 벡터 로드
    # -----------------------------------------------------------
    load_start_time = time.time()
    print("   ... DB에서 모든 데이터 및 벡터 로드 중...")
    
    sql = f"""SELECT product_id, image_path, image_vector, weaviate_uuid FROM {TABLE_NAME}"""
    mysql_cursor.execute(sql)
    
    for (product_id, image_path, image_vector_json, weaviate_uuid) in mysql_cursor:
        # JSON 문자열을 Python 리스트로 변환 후 NumPy 배열로 변환
        try:
            vector_list = json.loads(image_vector_json)
            vector_np = np.array(vector_list, dtype=np.float32)
        except Exception:
            print(f"⚠️ 경고: product_id {product_id}의 벡터 데이터 파싱 실패. 건너뜀.")
            continue

        # 모든 벡터 리스트에 저장
        data_item = {
            "product_id": product_id,
            "image_path": image_path,
            "vector": vector_np,
            "weaviate_uuid": weaviate_uuid
        }
        all_vectors.append(data_item)

        # 쿼리 대상 벡터 확인
        if product_id == QUERY_PRODUCT_ID:
            query_vector = vector_np
    
    load_end_time = time.time()
    
    if query_vector is None:
        print(f"❌ 오류: Product ID {QUERY_PRODUCT_ID}를 데이터베이스에서 찾을 수 없습니다.")
        mysql_cursor.close()
        mysql_conn.close()
        return

    print(f"✅ 데이터 로드 완료: 총 {len(all_vectors)}개 객체 (소요 시간: {load_end_time - load_start_time:.4f}초)")

    # -----------------------------------------------------------
    # 4-2. Python 메모리 내에서 유사도 계산 (Brute-force)
    # -----------------------------------------------------------
    calc_start_time = time.time()
    print("   ... Python 메모리 내에서 코사인 유사도 계산 중...")

    # 유사도 결과를 저장할 리스트
    similarity_results = []
    
    for item in all_vectors:
        # 쿼리 대상 자신은 제외
        if item["product_id"] == QUERY_PRODUCT_ID:
            continue
            
        similarity = cosine_similarity(query_vector, item["vector"])
        similarity_results.append({
            "product_id": item["product_id"],
            "image_path": item["image_path"],
            "similarity": similarity
        })
        
    # 유사도(similarity)가 높은 순서대로 정렬
    similarity_results.sort(key=itemgetter('similarity'), reverse=True)
    
    calc_end_time = time.time()
    
    # -----------------------------------------------------------
    # 4-3. 결과 출력 및 시간 측정 최종 보고
    # -----------------------------------------------------------
    print(f"✅ 유사도 계산 완료 (소요 시간: {calc_end_time - calc_start_time:.4f}초)")
    
    print("\n--- 유사 상품 검색 결과 (MySQL + Python Brute-force) ---")
    
    # 상위 QUERY_LIMIT 개만 출력
    for i, result in enumerate(similarity_results[:QUERY_LIMIT]):
        print(f"[{i+1}] 유사도: {result['similarity']:.4f}")
        print(f"  > Product ID: {result['product_id']}")
        print(f"  > Path: {result['image_path']}")
        print("---")
        
    total_end_time = time.time()
    total_time_taken = total_end_time - total_start_time

    print(f"\n✨ **최종 소요 시간 (DB 로드 + 유사도 계산): {total_time_taken:.4f}초**")

    # DB 연결 종료
    mysql_cursor.close()
    mysql_conn.close()
    print("👋 MySQL 클라이언트 연결 종료.")


if __name__ == "__main__":
    run_mysql_similarity_search()