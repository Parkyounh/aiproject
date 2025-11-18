# -*- coding: utf-8 -*-
# 1_mask_and_save_time.py

import os
import time  # time 모듈 추가
from PIL import Image
from utils import remove_background

# -----------------------------------------------------------
# 1. 환경 설정
# -----------------------------------------------------------
IMAGE_DIR = r"images\product_craw"
MASKED_DIR = r"images\product_craw_masked" # 마스킹된 이미지를 저장할 폴더

if not os.path.exists(MASKED_DIR):
    os.makedirs(MASKED_DIR)
    print(f"✅ 마스킹 이미지 저장 폴더 생성: {MASKED_DIR}")

image_paths = [os.path.join(IMAGE_DIR, f) for f in os.listdir(IMAGE_DIR)
               if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp",".avif"))]

if len(image_paths) == 0:
    print(f"❌ '{IMAGE_DIR}' 폴더에 이미지가 없습니다!")
    exit()

print(f"\n🚀 {len(image_paths)}개 이미지 마스킹 및 저장 시작...")

# -----------------------------------------------------------
# 2. 마스킹 처리 및 저장 (시간 측정 추가)
# -----------------------------------------------------------
total_start_time = time.time()  # 전체 시작 시간 기록

for path in image_paths:
    start_time = time.time()  # 개별 파일 시작 시간 기록
    
    try:
        input_image_pil = Image.open(path)
        
        # 1. 배경 제거 및 검은색 배경으로 변환
        masked_image = remove_background(input_image_pil)
        
        # 2. 파일 이름 설정
        filename = os.path.basename(path)
        save_path = os.path.join(MASKED_DIR, filename)
        
        # 3. 이미지 저장 (원본 확장자 유지)
        masked_image.save(save_path)
        
        end_time = time.time()  # 개별 파일 끝 시간 기록
        time_taken = end_time - start_time  # 소요 시간 계산
        
        print(f"✅ Masked and saved: {save_path} (소요 시간: {time_taken:.4f}초)")
        
    except Exception as e:
        print(f"❌ 파일 처리 오류 ({path}): {e}")

total_end_time = time.time() # 전체 끝 시간 기록
total_time_taken = total_end_time - total_start_time # 전체 소요 시간 계산

print("\n--- 마스킹 처리 완료 ---")
print(f"✨ **총 처리 시간: {total_time_taken:.4f}초**")