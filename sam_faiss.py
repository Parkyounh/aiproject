import os
import cv2
import torch
import numpy as np
import faiss
# CLIP 관련 라이브러리 제거
from PIL import Image
from sklearn.preprocessing import normalize # 벡터 정규화에 필요

# SAM 관련 라이브러리는 객체 마스크와 임베딩을 위해 유지합니다.
from segment_anything import sam_model_registry, SamPredictor


# ==========================
# 1. SAM 모델 로드
# ==========================
# SAM 설정 (객체 마스크 및 이미지 임베딩 추출 용도)
sam_checkpoint = "weights/sam_vit_h_4b8939.pth" # 실제 경로로 수정하세요
model_type = "vit_h"
device = "cuda" if torch.cuda.is_available() else "cpu" # GPU 사용 가능 여부 확인

# SAM 모델 로드
sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
sam.to(device=device)
sam_predictor = SamPredictor(sam) # 변수 이름 변경


# ==========================
# 2. 이미지 임베딩 생성 함수 (SAM 임베딩 사용, 마스크 적용)
# ==========================
# 🚨 SAM의 임베딩 추출 방식을 활용하도록 함수 로직을 변경합니다.
def get_sam_embedding_from_masked_object(image_path):
    # 1. 이미지 로드 및 SAM 마스크 추출
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise FileNotFoundError(f"Image not found at {image_path}")
        
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    
    # SAM에게 이미지 정보를 전달하고, 전체 이미지 임베딩 계산 (마스크와 무관)
    sam_predictor.set_image(image_rgb)
    
    # 🟢🟢🟢 바운딩 박스 프롬프트 사용 (중앙 80% 영역) 🟢🟢🟢
    H, W, _ = image_rgb.shape
    margin_ratio = 0.1 # 상하좌우 10% 여백
    x_min = int(W * margin_ratio)
    y_min = int(H * margin_ratio)
    x_max = int(W * (1 - margin_ratio))
    y_max = int(H * (1 - margin_ratio))
    
    input_box = np.array([[x_min, y_min, x_max, y_max]]) # [x_min, y_min, x_max, y_max]
    print(f"     -> SAM Bounding Box Prompt: {input_box[0]}")
    
    # 마스크 계산 (바운딩 박스를 프롬프트로 사용)
    masks, scores, logits = sam_predictor.predict(
        point_coords=None,
        point_labels=None,
        box=input_box,
        multimask_output=False,
    )
    
    if masks is None or not masks.any():
        print(f"⚠️ Warning: No main object mask found for {image_path}. Using full image.")
        mask = np.ones((H, W), dtype=bool)
    else:
        print(f"     -> SAM Mask Score: {scores[0]:.4f}")
        mask = masks[0]
        
    # 2. 마스크를 사용하여 배경 제거 (검은색으로 채우기)
    # 이미지 임베딩은 SAM 모델의 내부 기능(Image Encoder)에서 추출되므로,
    # 마스크 처리된 이미지는 저장 용도로만 사용합니다.
    masked_image_rgb = image_rgb * mask[:, :, np.newaxis]
    
    # 🚨🚨🚨 객체만 남긴 이미지 저장 로직 (폴더 이름: masked_nonclip) 🚨🚨🚨
    save_dir = "masked_nonclip" # 저장할 폴더 이름 변경
    os.makedirs(save_dir, exist_ok=True)
    
    base_name = os.path.basename(image_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    save_path = os.path.join(save_dir, f"{file_name_without_ext}_masked.png")
    
    # RGB를 BGR로 변환하여 저장 (OpenCV 기본 포맷)
    masked_image_bgr = cv2.cvtColor(masked_image_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(save_path, masked_image_bgr)
    print(f"     💾 Masked image saved to: {save_path}")
    # 🚨🚨🚨 저장 로직 끝 🚨🚨🚨

    # 3. SAM 이미지 임베딩 추출 (Mask와 무관하게 Image Encoder에서 추출)
    # 이 임베딩은 전체 이미지의 특징을 나타내지만, 마스킹된 이미지와의 유사도 비교에 사용됩니다.
    embedding = sam_predictor.get_image_embedding().cpu().numpy()
    
    return embedding.flatten()


# ==========================
# 3. 이미지 폴더의 모든 이미지 처리 및 임베딩 추출
# ==========================
image_dir = "images"
image_paths = [os.path.join(image_dir, f) for f in os.listdir(image_dir)
               if f.lower().endswith((".png", ".jpg", ".jpeg",".webp"))]

if len(image_paths) < 2:
    raise ValueError("❌ 비교할 이미지가 2개 이상 필요합니다!")

embeddings = []
for path in image_paths:
    print(f"🔹 Processing: {path}")
    # 수정된 SAM 임베딩 함수 사용
    emb = get_sam_embedding_from_masked_object(path)
    embeddings.append(emb)

embeddings = np.array(embeddings).astype("float32")


# 🚨🚨🚨 벡터 정규화 🚨🚨🚨
# L2 노름으로 나누어 정규화해야 L2 거리를 코사인 유사도로 변환 가능
embeddings = normalize(embeddings, axis=1, norm='l2')

print(f"\n✅ All SAM embeddings extracted. Shape: {embeddings.shape}")


# ==========================
# 4. Faiss 인덱스 생성 및 유사도 검색
# ==========================
dimension = embeddings.shape[1]
# L2 거리 기반 인덱스 사용
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)
print("✅ FAISS IndexFlatL2 built.")

# 5. 유사도 검색 (예: 첫 번째 이미지 기준)
query_idx = 0
query_vector = embeddings[query_idx].reshape(1, -1)

k = 5 # 검색할 유사 이미지 개수
distances, indices = index.search(query_vector, k=k) # L2 거리 검색

print("\n🔍 Query Image:", image_paths[query_idx])
print("📸 Most similar images:")

# 🚨🚨🚨 거리(L2)를 코사인 유사도로 변환 🚨🚨🚨
# 코사인 유사도 (Similarity) = 1 - (L2_Distance^2 / 2)
# 이는 벡터가 L2 정규화되었을 때만 성립합니다.
cosine_similarities = 1 - (distances ** 2) / 2

for rank, idx in enumerate(indices[0]):
    similarity = cosine_similarities[0][rank]
    
    # 첫 번째 결과는 쿼리 이미지 자신
    if rank == 0:
        print(f"⭐ Query itself: {image_paths[idx]} (similarity: {similarity:.4f})")
    else:
        print(f"{rank}. {image_paths[idx]} (similarity: {similarity:.4f})")