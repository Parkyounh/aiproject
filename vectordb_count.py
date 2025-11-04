import sys
import weaviate

# -----------------------------------------------------------
# 0. 환경 설정
# -----------------------------------------------------------
WEAVIATE_HOST = "localhost"
WEAVIATE_PORT = 8090        
WEAVIATE_CLASS_NAME = "ImageObject"

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
# 2. 데이터 개수 확인
# ==========================
print("\n--- DB 데이터 개수 확인 ---")
try:
    # aggregate 메서드를 사용하여 객체의 총 개수를 가져옵니다.
    result = collection.aggregate.over_all(total_count=True)
    
    total_count = result.total_count
    
    if total_count is not None:
        print(f"**총 저장된 객체 개수:** {total_count}개")
    else:
        print("⚠️ 객체 개수를 확인할 수 없습니다.")

except Exception as e:
    print(f"❌ 데이터 개수 조회 중 오류 발생: {e}")
    
# ==========================
# 3. 연결 종료
# ==========================
client.close()
print("👋 Weaviate 클라이언트 연결 종료.")