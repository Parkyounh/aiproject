import os
import cv2
import torch
import numpy as np
import faiss
# CLIP 관련 라이브러리
import clip 
import sys
from PIL import Image

# 🚨🚨🚨 rembg 라이브러리 import 🚨🚨🚨
try:
    from rembg import remove
except ImportError:
    print("🚨 오류: rembg 라이브러리가 설치되지 않았습니다. 'pip install rembg'를 실행하세요.")
    sys.exit()

# -----------------------------------------------------------
# 1. SAM 관련 코드 제거 및 CLIP 모델 로드
# -----------------------------------------------------------

# SAM 모델 로드 및 SamPredictor 관련 코드는 모두 제거했습니다.
device = "cuda" if torch.cuda.is_available() else "cpu"

# CLIP 모델 로드 (동일)
clip_model, preprocess = clip.load("ViT-B/32", device=device)
clip_model.eval() 
print(f"✅ CLIP 모델 로드 완료. (Device: {device})")


def get_clip_embedding_from_masked_object(image_path):
    """
    1. rembg 라이브러리를 사용하여 이미지 배경을 제거합니다.
    2. 배경이 제거된 이미지 (투명 배경)를 검은색 배경으로 변환하여 CLIP에 입력합니다.
    3. CLIP 임베딩을 추출하고 L2 정규화합니다.
    """
    
    # 1. 이미지 로드 (PIL Image 사용)
    try:
        input_image_pil = Image.open(image_path).convert("RGB")
    except FileNotFoundError:
        raise FileNotFoundError(f"Image not found at {image_path}")
        
    # 2. 🚨🚨🚨 rembg를 사용한 배경 제거 🚨🚨🚨
    # rembg.remove()는 배경이 투명한 RGBA PIL Image를 반환합니다.
    # U2Net 등의 모델을 사용하여 배경을 분리합니다.
    print("    -> rembg를 사용하여 배경 제거 중...")
    output_image_rgba = remove(input_image_pil)
    
    # 3. 투명 배경 (RGBA) 이미지를 검은색 배경 (RGB) 이미지로 변환
    # CLIP은 투명도(Alpha) 채널을 잘 처리하지 못하므로, 배경을 검은색으로 처리합니다.
    
    # a. Alpha 채널 추출
    alpha_channel = output_image_rgba.split()[-1]
    
    # b. RGB 채널과 마스크 결합
    masked_image_rgb = Image.new('RGB', output_image_rgba.size, (0, 0, 0)) # 검은색 배경
    masked_image_rgb.paste(output_image_rgba, mask=alpha_channel)
    
    # 🚨🚨🚨 객체만 남긴 이미지 저장 로직 (투명 배경 처리 후) 🚨🚨🚨
    save_dir = "masked_images_rembg" # 폴더 이름 변경
    os.makedirs(save_dir, exist_ok=True)
    base_name = os.path.basename(image_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    # RGBA 결과물을 저장하여 투명 배경을 확인하거나, RGB 결과물을 저장 (여기서는 RGB)
    save_path = os.path.join(save_dir, f"{file_name_without_ext}_masked.png")
    
    # OpenCV를 사용하지 않고 PIL로 바로 저장
    masked_image_rgb.save(save_path) 
    print(f"    💾 Masked image saved to: {save_path}")
    # 🚨🚨🚨 저장 로직 끝 🚨🚨🚨
    
    # 4. CLIP 임베딩 추출
    image_tensor = preprocess(masked_image_rgb).unsqueeze(0).to(device)
    
    with torch.no_grad():
        embedding = clip_model.encode_image(image_tensor)
        
    # 벡터 정규화
    embedding_np = embedding.cpu().numpy().astype("float32")
    embedding_norm = embedding_np / np.linalg.norm(embedding_np)
    
    return embedding_norm.flatten()


# ==========================
# 3. 이미지 폴더의 모든 이미지 처리 및 임베딩 추출 (동일)
# ==========================
image_dir = "images"
image_paths = [os.path.join(image_dir, f) for f in os.listdir(image_dir) 
               if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]

if len(image_paths) < 2:
    raise ValueError("❌ 비교할 이미지가 2개 이상 필요합니다!")

embeddings = []
for path in image_paths:
    print(f"\n🔹 Processing: {path}")
    emb = get_clip_embedding_from_masked_object(path) 
    embeddings.append(emb)

embeddings = np.array(embeddings).astype("float32")
print(f"\n✅ All embeddings extracted. Total images: {len(embeddings)}")


# ==========================
# 4. Faiss 인덱스 생성 및 검색 (동일)
# ==========================
dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension) 
index.add(embeddings)
print(f"✅ FAISS index built with {len(embeddings)} images using CLIP and IP Index.")

query_idx = 0
query_vector = embeddings[query_idx].reshape(1, -1)
distances, indices = index.search(query_vector, k=5) 

print("\n" + "=" * 50)
print(f"✨ 최종 유사도 검색 결과 (rembg 객체 + CLIP 임베딩)")
print("=" * 50)
print(f"🔍 Query Image: {image_paths[query_idx]}")
print("📸 Most similar images:")

for rank, idx in enumerate(indices[0]): 
    similarity = distances[0][rank]
    
    if rank == 0:
        print(f"⭐ Query itself: {image_paths[idx]} (similarity: {similarity:.4f})")
    else:
        print(f"{rank}. {image_paths[idx]} (similarity: {similarity:.4f})")
print("=" * 50)
