import os
import cv2
import torch
import numpy as np
import clip 
from PIL import Image
from sklearn.metrics.pairwise import cosine_similarity # 코사인 유사도 계산에 사용

# SAM 관련 라이브러리 (이전 코드와 동일하게 유지)
from segment_anything import sam_model_registry, SamPredictor

# ==========================
# 1. SAM 및 CLIP 모델 로드 (Faiss 사용 코드와 동일)
# ==========================
sam_checkpoint = "weights/sam_vit_h_4b8939.pth" 
model_type = "vit_h"
device = "cuda" if torch.cuda.is_available() else "cpu"

sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
sam.to(device=device)
sam_predictor = SamPredictor(sam)

clip_model, preprocess = clip.load("ViT-B/32", device=device)
clip_model.eval() 

# 이전 코드의 get_clip_embedding_from_masked_object 함수를 그대로 사용합니다.
# (이 함수는 임베딩 추출 및 L2 정규화까지 완료된 벡터를 반환합니다.)
def get_clip_embedding_from_masked_object(image_path):
    # (코드는 Faiss 사용 코드와 완전히 동일합니다. 중복을 피하기 위해 생략)
    # 1. 이미지 로드 및 SAM 마스크 추출...
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise FileNotFoundError(f"Image not found at {image_path}")
        
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    sam_predictor.set_image(image_rgb)
    
    H, W, _ = image_rgb.shape
    margin_ratio = 0.1
    x_min = int(W * margin_ratio); y_min = int(H * margin_ratio)
    x_max = int(W * (1 - margin_ratio)); y_max = int(H * (1 - margin_ratio))
    input_box = np.array([[x_min, y_min, x_max, y_max]])
    print(f"    -> SAM Bounding Box Prompt: {input_box[0]}")

    masks, scores, _ = sam_predictor.predict(
        point_coords=None, point_labels=None, box=input_box, multimask_output=False
    )
    
    if masks is None or not masks.any():
        print(f"⚠️ Warning: No main object mask found for {image_path}. Using full image.")
        mask = np.ones((H, W), dtype=bool)
    else:
        print(f"    -> SAM Mask Score: {scores[0]:.4f}")
        mask = masks[0]
        
    masked_image_rgb = image_rgb * mask[:, :, np.newaxis]
    
    # 이미지 저장 (masked_images 폴더)
    save_dir = "masked_images"; os.makedirs(save_dir, exist_ok=True)
    base_name = os.path.basename(image_path)
    file_name_without_ext = os.path.splitext(base_name)[0]
    save_path = os.path.join(save_dir, f"{file_name_without_ext}_masked.png")
    masked_image_bgr = cv2.cvtColor(masked_image_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(save_path, masked_image_bgr)
    print(f"    💾 Masked image saved to: {save_path}")
    
    image_pil = Image.fromarray(masked_image_rgb)
    image_tensor = preprocess(image_pil).unsqueeze(0).to(device)
    
    with torch.no_grad():
        embedding = clip_model.encode_image(image_tensor)
        
    embedding_np = embedding.cpu().numpy().astype("float32")
    # L2 정규화 (코사인 유사도 계산을 위해 필수)
    embedding_norm = embedding_np / np.linalg.norm(embedding_np) 
    
    return embedding_norm.flatten()


# ==========================
# 2. 이미지 처리 및 임베딩 추출 (Faiss 사용 코드와 동일)
# ==========================
image_dir = "images"
image_paths = [os.path.join(image_dir, f) for f in os.listdir(image_dir) 
               if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))]

if len(image_paths) < 2:
    raise ValueError("❌ 비교할 이미지가 2개 이상 필요합니다!")

embeddings = []
for path in image_paths:
    print(f"🔹 Processing: {path}")
    emb = get_clip_embedding_from_masked_object(path) 
    embeddings.append(emb)

embeddings = np.array(embeddings).astype("float32")
print(f"✅ All embeddings extracted. Total images: {len(embeddings)}")


# ==========================
# 3. 🚨🚨🚨 Faiss를 사용하지 않고 유사도 검색 🚨🚨🚨
# ==========================
query_idx = 0
query_vector = embeddings[query_idx].reshape(1, -1)
k = 5

# NumPy를 사용하여 쿼리 벡터와 모든 임베딩 간의 코사인 유사도를 한 번에 계산
# L2 정규화된 벡터를 사용했으므로, 행렬 곱(내적) 결과가 코사인 유사도입니다.
similarities = embeddings.dot(query_vector.T).flatten()

# 유사도 결과를 (유사도, 인덱스) 쌍으로 묶어 정렬
sorted_indices = np.argsort(similarities)[::-1] # 내림차순 정렬

# 상위 k개 결과만 추출
top_k_indices = sorted_indices[:k]
top_k_similarities = similarities[top_k_indices]


print("\n" + "=" * 50)
print("✨ Faiss 없이 NumPy로 유사도 검색 결과")
print(f"🔍 Query Image: {image_paths[query_idx]}")
print("📸 Most similar images:")
print("=" * 50)

for rank, idx in enumerate(top_k_indices):
    similarity = top_k_similarities[rank]
    
    if rank == 0:
        print(f"⭐ Query itself: {image_paths[idx]} (similarity: {similarity:.4f})")
    else:
        print(f"{rank}. {image_paths[idx]} (similarity: {similarity:.4f})")

print("=" * 50)