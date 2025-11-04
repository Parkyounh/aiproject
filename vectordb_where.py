import sys
import weaviate
from weaviate.classes.query import Filter

# -----------------------------------------------------------
# 0. 환경 설정
# -----------------------------------------------------------
WEAVIATE_HOST = "localhost"
WEAVIATE_PORT = 8090        
WEAVIATE_CLASS_NAME = "ImageObject"

# 🚨🚨 검색할 파일 이름 (예: images\4.webp) 🚨🚨
SEARCH_IMAGE_PATH = "images\\4.webp" 

# ==========================
# 1. Weaviate 클라이언트 연결
# ==========================
try:
    client = weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=WEAVIATE_PORT,
        grpc_port=50051
    )
    collection = client.collections.get(WEAVIATE_CLASS_NAME)
    print(f"✅ Weaviate 클라이언트 연결 성공.")
except Exception as e:
    print(f"❌ Weaviate 연결 실패. 오류: {e}")
    sys.exit()

# ==========================
# 2. 이미지 이름으로 객체 검색 (Where 필터)
# ==========================
print(f"\n--- 이미지 이름으로 객체 검색 시작: {SEARCH_IMAGE_PATH} ---")
try:
    # Where 필터를 사용하여 imagePath 속성 값이 일치하는 객체를 검색합니다.
    response = collection.query.fetch_objects(
        filters=Filter.by_property("imagePath").equal(SEARCH_IMAGE_PATH),
        return_properties=["imagePath"],
        limit=10 
    )

    if response.objects:
        print(f"✅ 총 {len(response.objects)}개의 객체 조회 성공:")
        print("=" * 40)
        for i, obj in enumerate(response.objects):
            uuid_short = str(obj.uuid).split('-')[0]
            path = obj.properties.get('imagePath', 'N/A')
            print(f"  {i+1}. ID: {uuid_short}..., Path: **{path}**")
        print("=" * 40)
    else:
        print(f"⚠️ 검색어 '{SEARCH_IMAGE_PATH}'와 일치하는 객체가 없습니다.")

except Exception as e:
    print(f"❌ 객체 검색 중 오류 발생: {e}")

# ==========================
# 3. 연결 종료
# ==========================
client.close()
print("👋 Weaviate 클라이언트 연결 종료.")