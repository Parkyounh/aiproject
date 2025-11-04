import os
import io
import sys
import base64
from PIL import Image
import weaviate
import torch
import numpy as np

# 🚨🚨🚨 rembg 라이브러리 import 🚨🚨🚨
try:
    from rembg import remove
except ImportError:
    print("🚨 오류: rembg 라이브러리가 설치되지 않았습니다. 'pip install rembg'를 실행하세요.")
    sys.exit()

# -----------------------------------------------------------
# 0. Weaviate 및 환경 설정
# -----------------------------------------------------------
# Weaviate v4 클라이언트 초기화 방식에 맞춰 host와 port를 분리하여 정의합니다.
WEAVIATE_HOST = "localhost" 
WEAVIATE_PORT = 8080      
WEAVIATE_CLASS_NAME = "ImageObject"

# CLIP 모델은 Weaviate 인스턴스에 의해 자동으로 로드됩니다.
device = "cuda" if torch.cuda.is_available() else "cpu"

print(f"✅ 환경 설정 완료. (Weaviate Target: {WEAVIATE_HOST}:{WEAVIATE_PORT}, Device: {device})")


# -----------------------------------------------------------
# 1. 이미지 처리 함수 (rembg 사용)
# -----------------------------------------------------------

def process_image_for_weaviate(image_path):
    """
    1. rembg를 사용하여 이미지 배경을 제거합니다.
    2. 배경이 투명한 PNG 이미지를 Base64로 인코딩하여 반환합니다.
    """
    
    try:
        input_image_pil = Image.open(image_path).convert("RGB")
    except FileNotFoundError:
        raise FileNotFoundError(f"Image not found at {image_path}")
        
    print("    -> rembg를 사용하여 배경 제거 중...")
    output_image_rgba = remove(input_image_pil)
    
    # PIL Image를 바이트 스트림으로 변환 (PNG 포맷 유지)
    buffer = io.BytesIO()
    output_image_rgba.save(buffer, format="PNG") 
    
    # Base64 인코딩
    base64_bytes = base64.b64encode(buffer.getvalue())
    base64_string = base64_bytes.decode('utf-8')
    
    return base64_string


# ==========================
# 2. Weaviate 인덱스 설정 및 데이터 업로드
# ==========================

# 1. 클라이언트 연결 (최신 Weaviate v4 클라이언트 방식 적용)
try:
    # 🚨🚨🚨 v4 클래스 이름으로 변경: weaviate.Client -> weaviate.WeaviateClient 🚨🚨🚨
    client = weaviate.WeaviateClient(
        host=WEAVIATE_HOST, 
        port=WEAVIATE_PORT,
        scheme='http' 
    )
    client.is_live() # 연결 확인
    print("✅ Weaviate 클라이언트 연결 성공.")
except Exception as e:
    print(f"❌ Weaviate 클라이언트 연결 실패. Docker 컨테이너가 실행 중인지 확인하세요.")
    print(f"오류: {e}")
    sys.exit()


# 2. 스키마 정의 및 클래스 생성
if client.schema.exists(WEAVIATE_CLASS_NAME):
    client.schema.delete_class(WEAVIATE_CLASS_NAME)
    print(f"🗑️ 기존 클래스 '{WEAVIATE_CLASS_NAME}' 삭제 완료.")

schema = {
    "class": WEAVIATE_CLASS_NAME,
    "description": "rembg 처리된 이미지 객체 클래스",
    "moduleConfig": {
        "img2vec-clip": {
            "imageFields": ["image"],
            "targetDevice": device,
            "model": "ViT-B/32"
        }
    },
    "properties": [
        {
            "dataType": ["string"],
            "name": "imagePath",
            "description": "원본 이미지 파일 경로"
        },
        {
            "dataType": ["blob"],
            "name": "image",
            "description": "rembg 처리된 Base64 이미지 데이터"
        }
    ]
}

client.schema.create_class(schema)
print(f"✨ Weaviate 클래스 '{WEAVIATE_CLASS_NAME}' 생성 완료.")


# 3. 데이터 로드 및 배치 업로드
image_dir = "images"
image_paths = [os.path.join(image_dir, f) for f in os.listdir(image_dir) 
               if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]

if len(image_paths) == 0:
    raise ValueError(f"❌ '{image_dir}' 폴더에 이미지가 없습니다!")

client.batch.configure(batch_size=10, timeout_retries=3)
with client.batch as batch:
    for path in image_paths:
        print(f"\n🔹 Processing: {path}")
        base64_image = process_image_for_weaviate(path)
        
        data_object = {
            "imagePath": path,
            "image": base64_image 
        }
        
        batch.add_data_object(data_object, WEAVIATE_CLASS_NAME)

print(f"\n✅ All {len(image_paths)} images processed and sent to Weaviate for indexing.")


# ==========================
# 3. 유사도 검색 (Weaviate 사용)
# ==========================
query_image_path = image_paths[0] 

# 1. 쿼리 이미지 처리 및 Base64 인코딩
query_base64 = process_image_for_weaviate(query_image_path)


# 2. Weaviate 검색 쿼리 실행
result = client.query.get(
    WEAVIATE_CLASS_NAME,
    ["imagePath"] 
).with_near_image(
    {"image": query_base64}
).with_additional(
    ["distance"]
).with_limit(5).do()


# 3. 결과 출력
print("\n" + "=" * 50)
print(f"✨ 최종 유사도 검색 결과 (Weaviate Vector DB)")
print("=" * 50)
print(f"🔍 Query Image: {query_image_path}")

if 'data' in result and 'Get' in result['data'] and result['data']['Get'][WEAVIATE_CLASS_NAME]:
    results = result['data']['Get'][WEAVIATE_CLASS_NAME]
    
    print("📸 Most similar images:")
    for rank, item in enumerate(results):
        path = item['imagePath']
        distance = item['_additional']['distance']
        
        if path == query_image_path:
             print(f"⭐ Query itself: {path} (distance: {distance:.4f})")
        else:
             print(f"{rank}. {path} (distance: {distance:.4f})")
else:
    print("❌ 검색 결과가 없습니다. Weaviate 로그를 확인하세요.")

print("=" * 50)