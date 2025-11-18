# get_vector_by_product_id.py
# 특정 product_id를 사용하여 Weaviate DB에서 512차원 벡터를 조회합니다.

import sys
from weaviate.classes.query import Filter

# utils.py에서 정의된 함수/변수 임포트
from utils import connect_to_weaviate, WEAVIATE_CLASS_NAME 

# -----------------------------------------------------------
# 1. 조회할 Product ID 설정
# -----------------------------------------------------------
# 📝 여기에 실제로 DB에 저장된 product_id 값을 입력하세요.
TARGET_PRODUCT_ID = 20787518 # 예시 ID
VECTOR_DIMENSION = 512 # CLIP ViT-B/32 모델의 기본 출력 차원

print(f"\n🔍 Product ID {TARGET_PRODUCT_ID}의 512차원 벡터 조회 시작...")

# -----------------------------------------------------------
# 2. Weaviate 연결 및 컬렉션 가져오기
# -----------------------------------------------------------
try:
    client = connect_to_weaviate()
    collection = client.collections.get(WEAVIATE_CLASS_NAME)
    print(f"🔄 컬렉션 '{WEAVIATE_CLASS_NAME}' 연결 성공.")
except Exception as e:
    print(f"❌ Weaviate 연결 또는 컬렉션 가져오기 실패: {e}")
    sys.exit()

# -----------------------------------------------------------
# 3. Where 필터링을 이용한 객체 조회
# -----------------------------------------------------------
try:
    # 📌 Filter.by_property를 사용하여 product_id가 TARGET_PRODUCT_ID와 일치하는 객체를 찾습니다.
    # 📌 include_vector=True를 설정하여 벡터 값을 결과에 포함시킵니다.
    response = collection.query.fetch_objects(
        filters=Filter.by_property("product_id").equal(TARGET_PRODUCT_ID),
        limit=1, # product_id는 고유하다고 가정하고 1개만 조회
        include_vector=True,
        return_properties=["imagePath"] # 벡터 외에 이미지 경로도 함께 반환
    )

    if response.objects:
        # 첫 번째 객체 (가장 관련성 높은 객체)를 가져옵니다.
        found_object = response.objects[0]
        
        # 4. 결과 출력
        # 벡터는 obj.vector에 딕셔너리 형태로 저장되어 있습니다. 
        # (기본적으로 'default' 키에 저장)
        vector_data = found_object.vector
        
        if 'default' in vector_data and vector_data['default'] is not None:
            vector_value = vector_data['default']
            
            # 벡터가 512차원인지 확인
            if len(vector_value) == VECTOR_DIMENSION:
                print(f"\n✅ Product ID {TARGET_PRODUCT_ID}의 벡터 조회 성공!")
                print(f"  > 이미지 경로: {found_object.properties.get('imagePath')}")
                print(f"  > **벡터 차원**: {len(vector_value)}차원")
                print(vector_value) # 전체 벡터 값을 보려면 이 주석을 해제하세요.
            else:
                print(f"❌ 조회된 벡터의 차원이 예상과 다릅니다: {len(vector_value)}차원")
        else:
            print("❌ 객체는 찾았으나 'default' 벡터가 존재하지 않습니다.")
    else:
        print(f"⚠️ Product ID {TARGET_PRODUCT_ID}에 해당하는 객체를 찾을 수 없습니다.")

except Exception as e:
    print(f"\n❌ Weaviate 조회 중 오류 발생: {e}")

finally:
    client.close()
    print("👋 Weaviate 클라이언트 연결 종료.")