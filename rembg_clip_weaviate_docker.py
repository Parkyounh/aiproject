import os
import sys
import torch
import numpy as np
from PIL import Image
import weaviate
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery
# 🚨 DataObject import는 이미 상단에 잘 되어 있습니다.
from weaviate.classes.data import DataObject 
import warnings
warnings.filterwarnings('ignore')

# 🚨🚨🚨 rembg 및 CLIP 라이브러리 import 🚨🚨🚨
try:
    from rembg import remove
    import clip
except ImportError:
    print("🚨 오류: rembg 또는 CLIP 라이브러리가 설치되지 않았습니다. 'pip install rembg clip'를 실행하세요.")
    sys.exit()

print("🚀 시스템 초기화 중...")

# -----------------------------------------------------------
# 0. 환경 및 모델 설정
# -----------------------------------------------------------
WEAVIATE_HOST = "localhost"
WEAVIATE_PORT = 8090  # 🚨 8090 포트 사용 확인
WEAVIATE_CLASS_NAME = "ImageObject"

# CLIP 모델 직접 로드 (Python이 벡터를 생성)
device = "cuda" if torch.cuda.is_available() else "cpu"
try:
    clip_model, preprocess = clip.load("ViT-B/32", device=device)
    clip_model.eval()
    print(f"✅ CLIP 모델 로드 완료. (Device: {device})")
except Exception as e:
    print(f"❌ CLIP 모델 로드 실패: {e}")
    sys.exit()

# -----------------------------------------------------------
# 1. 이미지 전처리 및 벡터 변환 함수
# -----------------------------------------------------------

def remove_background(image: Image.Image) -> Image.Image:
    """rembg를 사용해 배경 제거 후 검은색 배경으로 변환"""
    try:
        output_rgba = remove(image.convert("RGB"))
        alpha_channel = output_rgba.split()[-1]
        image_with_black_bg = Image.new('RGB', output_rgba.size, (0, 0, 0))
        image_with_black_bg.paste(output_rgba, mask=alpha_channel)
        return image_with_black_bg
    except Exception:
        return image.convert("RGB")

def image_to_vector(image: Image.Image, remove_bg: bool = True) -> list:
    """CLIP을 사용해 이미지를 벡터로 변환하고 L2 정규화"""
    if remove_bg:
        image_processed = remove_background(image)
    else:
        image_processed = image.convert("RGB")

    image_input = preprocess(image_processed).unsqueeze(0).to(device)

    with torch.no_grad():
        image_features = clip_model.encode_image(image_input)
        image_features /= image_features.norm(dim=-1, keepdim=True)

    return image_features.cpu().numpy().flatten().tolist()

# ==========================
# 2. Weaviate 클라이언트 연결 및 스키마 설정
# ==========================

# 1. 클라이언트 연결 (Docker 서버에 연결)
try:
    client = weaviate.connect_to_local(
        host=WEAVIATE_HOST,
        port=WEAVIATE_PORT, # 8090 포트 사용
        grpc_port=50051
    )
    client.is_live()
    print(f"✅ Weaviate 클라이언트 연결 성공. (Docker Server: {WEAVIATE_HOST}:{WEAVIATE_PORT})")
except Exception as e:
    print(f"❌ Weaviate 클라이언트 연결 실패. Docker 컨테이너가 실행 중인지 확인하세요.")
    print(f"오류: {e}")
    sys.exit()

# 2. 컬렉션 정의 및 생성
try:
    if client.collections.exists(WEAVIATE_CLASS_NAME):
        client.collections.delete(WEAVIATE_CLASS_NAME)
        print(f"🗑️ 기존 컬렉션 '{WEAVIATE_CLASS_NAME}' 삭제 완료.")

    collection = client.collections.create(
        name=WEAVIATE_CLASS_NAME,
        vectorizer_config=Configure.Vectorizer.none(),
        properties=[
            Property(name="imagePath", data_type=DataType.TEXT, description="원본 이미지 파일 경로"),
        ]
    )
    print(f"✨ Weaviate 컬렉션 '{WEAVIATE_CLASS_NAME}' 생성 완료.")

except Exception as e:
    print(f"❌ 컬렉션 생성 실패: {e}")
    sys.exit()
    
# ==========================
# 3. 데이터 로드 및 업로드 (최종 수정: DataObject 사용)
# ==========================
image_dir = "images"
image_paths = [os.path.join(image_dir, f) for f in os.listdir(image_dir)
               if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]

if len(image_paths) == 0:
    print(f"❌ '{image_dir}' 폴더에 이미지가 없습니다!")
    sys.exit()

# 🚨 컬렉션 객체를 가져옵니다. 🚨
collection = client.collections.get(WEAVIATE_CLASS_NAME)

# 🚨 삽입할 객체들을 DataObject로 리스트에 모읍니다. 🚨
data_objects_to_insert = []
print("\n🔄 데이터 객체 및 벡터 생성 시작...")

for path in image_paths:
    print(f"🔹 Processing: {path}")
    
    try:
        input_image_pil = Image.open(path)
        # Python에서 직접 벡터를 계산합니다.
        vector = image_to_vector(input_image_pil, remove_bg=True)

        # 🚨🚨🚨 추가된 검증 로직 시작 🚨🚨🚨
        if vector and len(vector) > 0:
            print(f"✅ Vector OK: Length={len(vector)}, First Value={vector[0]:.6f}")
        else:
            # 벡터 생성에 실패했거나 비어있는 경우 경고를 출력합니다.
            print(f"❌ WARNING: Vector is EMPTY or None for {path}. Skipping or may cause DB errors.")
            # 벡터가 비어있으면 다음 파일로 넘어가는 것이 안전합니다.
            if not vector:
                continue 
        # 🚨🚨🚨 추가된 검증 로직 끝 🚨🚨🚨
        
        data_object_properties = {
            "imagePath": path,
        }
        
        # 🚨 DataObject 클래스를 사용하여 객체 생성 및 리스트에 추가 (문제 해결 구문) 🚨
        data_objects_to_insert.append(
            DataObject(
                properties=data_object_properties,
                vector=vector
            )
        )
        
    except Exception as e:
        print(f"❌ 파일 처리 오류 ({path}): {e}")

# 🚨 insert_many를 사용하여 한 번에 데이터 삽입 🚨
print(f"\n📦 Weaviate에 {len(data_objects_to_insert)}개 데이터 전송 중...")

try:
    # insert_many는 DataObject 리스트를 받아 자동으로 배치 전송합니다.
    collection.data.insert_many(data_objects_to_insert)
    print(f"\n✅ All {len(data_objects_to_insert)} images processed and sent to Weaviate for indexing.")

except Exception as e:
    print(f"\n❌ Weaviate 삽입 최종 실패: {e}")
    sys.exit()

# ==========================
# 4. 유사도 검색 (Weaviate 사용)
# ==========================
query_image_path = image_paths[0] 

try:
    query_image_pil = Image.open(query_image_path)
    query_vector = image_to_vector(query_image_pil, remove_bg=True)
except Exception as e:
    print(f"❌ 쿼리 이미지 처리 실패: {e}")
    sys.exit()

print(f"\n📊 Weaviate 벡터 검색 중... (Query: {query_image_path})")

result = collection.query.near_vector(
    near_vector=query_vector,
    limit=5,
    return_metadata=MetadataQuery(distance=True)
)

# 3. 결과 출력
print("\n" + "=" * 50)
print(f"✨ 최종 유사도 검색 결과 (Weaviate Vector DB)")
print("=" * 50)
print(f"🔍 Query Image: {query_image_path}")

if result.objects:
    print("📸 Most similar images:")
    for rank, item in enumerate(result.objects):
        path = item.properties["imagePath"]
        distance = item.metadata.distance
        
        if path == query_image_path:
            print(f"⭐ Query itself: {path} (distance: {distance:.4f})")
        else:
            similarity = 1 - distance
            print(f"{rank+1}. {path} (similarity: {similarity:.4f} / distance: {distance:.4f})")
else:
    print("❌ 검색 결과가 없습니다. Weaviate 로그를 확인하세요.")

print("=" * 50)