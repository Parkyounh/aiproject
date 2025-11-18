# init_db.py
import sys
from utils import connect_to_weaviate, WEAVIATE_CLASS_NAME
from weaviate.classes.config import Property, DataType, Configure

print("🚀 init_db.py 시작")

client = connect_to_weaviate()

try:
    # 기존 컬렉션 삭제
    if client.collections.exists(WEAVIATE_CLASS_NAME):
        client.collections.delete(WEAVIATE_CLASS_NAME)
        print(f"🗑️ 기존 컬렉션 '{WEAVIATE_CLASS_NAME}' 삭제 완료.")

    # 새 컬렉션 생성
    collection = client.collections.create(
        name=WEAVIATE_CLASS_NAME,
        vectorizer_config=Configure.Vectorizer.none(),   # 벡터 직접 제공
        properties=[
            Property(name="imagePath", data_type=DataType.TEXT),
            Property(name="product_id", data_type=DataType.NUMBER),
        ],
    )

    print(f"✨ Weaviate 컬렉션 '{WEAVIATE_CLASS_NAME}' 재생성 완료.")

except Exception as e:
    print(f"❌ 컬렉션 초기화 실패: {e}")
    sys.exit()

finally:
    client.close()
    print("👋 Weaviate 클라이언트 연결 종료.")
