
import os
import cv2
import torch
import numpy as np
import faiss
# CLIP 관련 라이브러리 추가
import clip 
from PIL import Image

# SAM 관련 라이브러리는 객체 마스크를 위해 유지합니다.
from segment_anything import sam_model_registry, SamPredictor

# ==========================
# 1. SAM 및 CLIP 모델 로드
# ==========================
# SAM 설정 (객체 마스크 추출 용도)
sam_checkpoint = "weights/sam_vit_h_4b8939.pth" # 실제 경로로 수정하세요
model_type = "vit_h"
device = "cuda" if torch.cuda.is_available() else "cpu"

# SAM 모델 로드
sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
sam.to(device=device)
sam_predictor = SamPredictor(sam) # 변수 이름 변경

# 🚨🚨🚨 CLIP 모델 로드 🚨🚨🚨
# ViT-B/32는 일반적인 선택입니다. 더 좋은 성능을 원하면 ViT-L/14 등을 사용하세요.
clip_model, preprocess = clip.load("ViT-B/32", device=device)
clip_model.eval() 

def get_clip_embedding_from_masked_object(image_path):
    # 1. 이미지 로드 및 SAM 마스크 추출
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise FileNotFoundError(f"Image not found at {image_path}")
        
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    
    # SAM에게 이미지 정보를 전달
    sam_predictor.set_image(image_rgb)
    
    # 🟢🟢🟢 프롬프트 변경: 바운딩 박스 사용 🟢🟢🟢
    H, W, _ = image_rgb.shape
    # 중앙 80% 영역을 바운딩 박스로 설정 (주 객체가 중앙에 있다고 가정)
    margin_ratio = 0.1 # 상하좌우 10% 여백
    x_min = int(W * margin_ratio)
    y_min = int(H * margin_ratio)
    x_max = int(W * (1 - margin_ratio))
    y_max = int(H * (1 - margin_ratio))
    
    input_box = np.array([[x_min, y_min, x_max, y_max]]) # [x_min, y_min, x_max, y_max]
    print(f"    -> SAM Bounding Box Prompt: {input_box[0]}")
    # 🟢🟢🟢 변경 끝 🟢🟢🟢

    # 마스크 계산 (바운딩 박스를 프롬프트로 사용)
    masks, scores, logits = sam_predictor.predict(
        point_coords=None,       # 포인트 프롬프트 사용 안 함
        point_labels=None,       # 포인트 프롬프트 사용 안 함
        box=input_box,           # 바운딩 박스 프롬프트 사용
        multimask_output=False, # 가장 좋은 마스크 하나만 선택
    )
    
    if masks is None or not masks.any():
        print(f"⚠️ Warning: No main object mask found for {image_path}. Using full image.")
        mask = np.ones((H, W), dtype=bool)
    else:
        # 가장 점수가 높은 마스크 선택
        print(f"    -> SAM Mask Score: {scores[0]:.4f}")
        mask = masks[0] 

    # 2. 마스크를 사용하여 배경 제거 (검은색으로 채우기)
    # CLIP은 투명도(Alpha) 채널을 잘 처리하지 못하므로, 배경을 검은색으로 처리합니다.
    masked_image_rgb = image_rgb * mask[:, :, np.newaxis]
    
    # 🚨🚨🚨 객체만 남긴 이미지 저장 로직 (이전 요청으로 추가됨) 🚨🚨🚨
    save_dir = "masked_images" # 저장할 폴더 이름
    os.makedirs(save_dir, exist_ok=True)
    
    # 원본 파일명에서 확장자를 .png로 변경하여 저장
    base_name = os.path.basename(image_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    save_path = os.path.join(save_dir, f"{file_name_without_ext}_masked.png")
    
    # RGB를 BGR로 변환하여 저장 (OpenCV 기본 포맷)
    masked_image_bgr = cv2.cvtColor(masked_image_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(save_path, masked_image_bgr)
    print(f"    💾 Masked image saved to: {save_path}")
    # 🚨🚨🚨 저장 로직 끝 🚨🚨🚨
    
    # 3. CLIP 임베딩 추출
    # NumPy 배열을 PIL Image로 변환하고 CLIP 전처리 적용
    image_pil = Image.fromarray(masked_image_rgb)
    image_tensor = preprocess(image_pil).unsqueeze(0).to(device)
    
    # CLIP 임베딩 계산
    with torch.no_grad():
        embedding = clip_model.encode_image(image_tensor)
        
    # 벡터 정규화는 CLIP 인코더 내부적으로 처리되지만, 안전을 위해 최종적으로 한 번 더 L2 정규화합니다.
    embedding_np = embedding.cpu().numpy().astype("float32")
    embedding_norm = embedding_np / np.linalg.norm(embedding_np)
    
    return embedding_norm.flatten()


# ==========================
# 3. 이미지 폴더의 모든 이미지 처리 및 임베딩 추출
# ==========================
image_dir = "images"
image_paths = [os.path.join(image_dir, f) for f in os.listdir(image_dir) 
               if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]

if len(image_paths) < 2:
    raise ValueError("❌ 비교할 이미지가 2개 이상 필요합니다!")

embeddings = []
for path in image_paths:
    print(f"🔹 Processing: {path}")
    # 수정된 CLIP 임베딩 함수 사용
    emb = get_clip_embedding_from_masked_object(path) 
    embeddings.append(emb)

embeddings = np.array(embeddings).astype("float32")


# ==========================
# 4. Faiss 인덱스 생성 (코사인 유사도를 위한 IndexFlatIP 사용)
# ==========================
dimension = embeddings.shape[1]
# 🚨🚨🚨 IndexFlatIP (내적) 사용: 정규화된 벡터의 내적은 코사인 유사도와 같습니다. 🚨🚨🚨
index = faiss.IndexFlatIP(dimension) 
index.add(embeddings)
print(f"✅ FAISS index built with {len(embeddings)} images using CLIP and IP Index.")


# ==========================
# 5. 유사도 검색 (예: 첫 번째 이미지 기준)
# ==========================
query_idx = 0
query_vector = embeddings[query_idx].reshape(1, -1)

# k=5로 변경하여 더 많은 유사 이미지를 확인합니다.
distances, indices = index.search(query_vector, k=5) 

print("\n🔍 Query Image:", image_paths[query_idx])
print("📸 Most similar images:")

# IndexFlatIP를 사용했기 때문에 'distances'가 곧 'similarity' 값입니다 (1에 가까울수록 유사).
for rank, idx in enumerate(indices[0]): 
    similarity = distances[0][rank]
    
    # 첫 번째 결과는 쿼리 이미지 자신이어야 합니다.
    if rank == 0:
        print(f"⭐ Query itself: {image_paths[idx]} (similarity: {similarity:.4f})")
    else:
        print(f"{rank}. {image_paths[idx]} (similarity: {similarity:.4f})")