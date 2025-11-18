import sys
import torch
import numpy as np
from PIL import Image
import weaviate
from weaviate.classes.data import DataObject
from weaviate.classes.config import Configure, Property, DataType
from weaviate.classes.query import MetadataQuery
import warnings
import pillow_heif
pillow_heif.register_heif_opener() 
warnings.filterwarnings('ignore')

# rembg 및 CLIP
try:
    from rembg import remove
    import clip
except ImportError:
    print("🚨 오류: rembg 또는 CLIP 라이브러리가 설치되지 않았습니다. 'pip install rembg clip' 실행")
    sys.exit()

# 환경 변수
WEAVIATE_HOST = "localhost"
WEAVIATE_PORT = 8090
WEAVIATE_CLASS_NAME = "ImageObject"
GRPC_PORT = 50051

# CLIP 모델
device = "cuda" if torch.cuda.is_available() else "cpu"
try:
    CLIP_MODEL, PREPROCESS = clip.load("ViT-B/32", device=device)
    CLIP_MODEL.eval()
except Exception as e:
    print(f"❌ CLIP 모델 로드 실패: {e}")
    sys.exit()

# -----------------------------------------------------------
# Weaviate 연결 ( 🔥 SDK 4.x 최신 방식 )
# -----------------------------------------------------------

def connect_to_weaviate():
    try:
        client = weaviate.connect_to_local(
            host=WEAVIATE_HOST,
            port=WEAVIATE_PORT,
            grpc_port=GRPC_PORT
        )
        client.is_live()
        return client
    except Exception as e:
        print(f"❌ Weaviate 클라이언트 연결 실패: {e}")
        sys.exit()

# -----------------------------------------------------------
# 이미지 처리
# -----------------------------------------------------------

def remove_background(image: Image.Image) -> Image.Image:
    try:
        output_rgba = remove(image.convert("RGB"))
        alpha = output_rgba.split()[-1]
        bg = Image.new('RGB', output_rgba.size, (0, 0, 0))
        bg.paste(output_rgba, mask=alpha)
        return bg
    except Exception:
        return image.convert("RGB")

def image_to_vector(image: Image.Image, remove_bg: bool = True) -> list:
    if remove_bg:
        image_processed = remove_background(image)
    else:
        image_processed = image.convert("RGB")

    img_input = PREPROCESS(image_processed).unsqueeze(0).to(device)

    with torch.no_grad():
        features = CLIP_MODEL.encode_image(img_input)
        features /= features.norm(dim=-1, keepdim=True)

    return features.cpu().numpy().flatten().tolist()
