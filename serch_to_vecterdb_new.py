# 3_search_from_db_optimized.py (순수 검색 시간 측정)

import sys
import time
from weaviate.classes.query import MetadataQuery, Filter 
from utils import connect_to_weaviate, WEAVIATE_CLASS_NAME

# -----------------------------------------------------------
# 1. 환경 설정 및 변수 입력 ( 여기서 값을 설정하세요)
# -----------------------------------------------------------
# 원하는 product_id 검색 설정 
QUERY_PRODUCT_ID = 20787518  # 🔍 쿼리할 대상의 product_id를 여기에 입력 (숫자)
QUERY_LIMIT = 5            # 🔢 원하는 유사 이미지 검색 결과 개수(limit)를 여기에 입력 (숫자)
#  --------------------- 
# -----------------------------------------------------------
# 2. DB 연결 및 쿼리 객체 선정 (벡터 추출)
# -----------------------------------------------------------
# 전체 프로세스의 시작 시간 기록 (참고용)
overall_start_time = time.time()

client = connect_to_weaviate()
collection = client.collections.get(WEAVIATE_CLASS_NAME)


print(f"\n🔄 product_id '{QUERY_PRODUCT_ID}'에 해당하는 객체의 벡터를 DB에서 추출 중...")

try:
    # product_id로 필터링하여 쿼리할 객체 1개를 조회합니다.
    # 이 시간은 '순수 검색 시간'에 포함되지 않습니다.
    response = collection.query.fetch_objects(
        limit=1,
        # Filter 클래스를 사용하여 필터링
        filters=Filter.by_property("product_id").equal(QUERY_PRODUCT_ID),
        return_properties=["imagePath", "product_id"],
        include_vector=True 
    )

    if not response.objects:
        print(f"❌ DB에서 product_id '{QUERY_PRODUCT_ID}'를 찾을 수 없습니다.")
        client.close()
        sys.exit()

    # 추출된 쿼리 객체 정보
    query_item = response.objects[0]
    query_image_path = query_item.properties["imagePath"]
    query_image_path = query_image_path.replace('\\', '/') 
    query_vector = query_item.vector
        
    # 딕셔너리 형태일 경우 'default' 키의 리스트만 사용하도록 변환
    if isinstance(query_vector, dict) and 'default' in query_vector:
        query_vector = query_vector['default']
        # print("💡 추출된 벡터 형식이 딕셔너리여서, 'default' 키의 값만 사용하도록 변환했습니다.")
    elif not isinstance(query_vector, list):
          print(f"❌ 쿼리 벡터가 예상치 않은 형식입니다: {type(query_vector)}")
          client.close()
          sys.exit()


except Exception as e:
    print(f"❌ DB에서 쿼리 객체 추출 실패: {e}")
    client.close()
    sys.exit()

print(f"✅ 쿼리 벡터 추출 성공. (Source: Product ID: {QUERY_PRODUCT_ID}, Image: {query_image_path})")

# -----------------------------------------------------------
# 3. 벡터 검색 실행 및 결과 출력 (순수 near_vector 시간 측정)
# -----------------------------------------------------------
print(f"\n📊 Weaviate 벡터 검색 중... (Query Limit: {QUERY_LIMIT}개)")

# 📌📌📌 순수 벡터 검색 시간 측정 시작 📌📌📌
search_start_time = time.time()

# near_vector 검색 실행
result = collection.query.near_vector(
    near_vector=query_vector, 
    limit=QUERY_LIMIT,
    return_metadata=MetadataQuery(distance=True, certainty=True),
)

search_end_time = time.time() # 검색 종료 시간 기록
search_time = search_end_time - search_start_time # 순수 near_vector 실행 시간

overall_end_time = time.time()
overall_time = overall_end_time - overall_start_time

# -----------------------------------------------------------
# 4. 결과 출력
# -----------------------------------------------------------
print("\n" + "=" * 50)
print(f"✨ 최종 유사도 검색 결과 (Weaviate Vector DB)")
print("=" * 50)
print(f"🔍 Query Source: Product ID: {QUERY_PRODUCT_ID} / Image: {query_image_path}")

if result.objects:
    print(f"📸 Most similar images (Top {QUERY_LIMIT}):")
    for rank, item in enumerate(result.objects):
        path = item.properties["imagePath"]
        item_product_id = item.properties.get("product_id", "N/A") 
        distance = item.metadata.distance if item.metadata.distance is not None else 0
        certainty = item.metadata.certainty if item.metadata.certainty is not None else (1 - distance)
        similarity = 1 - distance # 유사도 (1 - 거리) 계산
        
        print(f"{rank+1}. {path} (Product ID: {item_product_id}) [Similarity: {similarity:.4f} / Distance: {distance:.4f} / Certainty: {certainty:.4f}]")
else:
    print("❌ 검색 결과가 없습니다.")

print("=" * 50)
print(f"⏱️ **순수 벡터 검색 시간 (near_vector):** {search_time:.4f} 초")
print(f"⏱️ 전체 처리 시간 (벡터 추출 포함): {overall_time:.4f} 초")
print("=" * 50)

client.close()
print("👋 Weaviate 클라이언트 연결 종료.")