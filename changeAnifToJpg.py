import os
import time
from PIL import Image
from pillow_heif import register_heif_opener

# 📢 AVIF 파일 처리를 위해 Pillow에 핸들러를 등록합니다.
register_heif_opener()

def convert_avif_to_jpg_batch_ultimate(input_folder, output_folder):
    """
    지정된 입력 폴더의 AVIF 파일을 JPG로 변환하여 지정된 출력 폴더에 저장합니다.

    :param input_folder: 원본 .avif 파일이 있는 폴더 경로
    :param output_folder: 변환된 .jpg 파일이 저장될 폴더 경로
    """
    
    # 출력 폴더가 없으면 생성합니다.
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        print(f"✅ 출력 폴더 생성: {output_folder}")
    
    # 변환할 파일 리스트
    avif_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.avif')]
    total_start_time = time.time()
    conversion_results = []
    
    print(f"👉 폴더: **{input_folder}** 에서 총 {len(avif_files)} 개의 .avif 파일을 찾았습니다.")
    print(f"💾 결과는 **{output_folder}** 에 저장됩니다.")
    print("-" * 40)

    for index, filename in enumerate(avif_files):
        # 입력 파일 경로
        input_filepath = os.path.join(input_folder, filename)
        
        # 출력 파일 이름과 경로
        output_filename = os.path.splitext(filename)[0] + '.jpg'
        output_filepath = os.path.join(output_folder, output_filename)
        
        try:
            file_start_time = time.time()
            
            # 1. Image.open() 시도 (register_heif_opener 덕분)
            with Image.open(input_filepath) as img:
                # 2. JPG로 지정된 출력 경로에 저장
                img.save(output_filepath, 'jpeg', quality=85)
            
            file_end_time = time.time()
            time_taken = file_end_time - file_start_time
            conversion_results.append((filename, output_filename, time_taken, "성공"))
            print(f"✅ [{index + 1}/{len(avif_files)}] **{filename}** -> **{output_filename}** 변환 완료 (소요 시간: {time_taken:.4f}초)")

        except Exception as e:
            conversion_results.append((filename, output_filename, 0, "실패"))
            print(f"❌ [{index + 1}/{len(avif_files)}] **{filename}** 변환 실패: {str(e)}") 

    total_end_time = time.time()
    total_time = total_end_time - total_start_time
    
    print("-" * 40)
    print("✨ **변환 작업 요약**")
    print(f"* 총 파일 개수: {len(avif_files)}개")
    print(f"* 변환 성공: {len([r for r in conversion_results if r[3] == '성공'])}개")
    print(f"* 총 소요 시간: {total_time:.4f}초")
    
    if any(r[3] == '성공' for r in conversion_results):
        print("\n* **개별 파일별 소요 시간**:")
        for original, new, time_taken, status in conversion_results:
            if status == '성공':
                print(f"  - {original}: {time_taken:.4f}초")

# --- 실행 부분 ---
# 🚨 1. 원본 AVIF 파일이 있는 경로를 지정하세요. (현재 사용하시던 경로)
input_directory = r'C:\Users\DU\.spyder-py3\aiproject\images\product_tem' 

# 🚨 2. 변환된 JPG 파일이 저장될 경로를 지정하세요. (예: input_directory 옆의 'jpg_output' 폴더)
output_directory = r'C:\Users\DU\.spyder-py3\aiproject\images\product_jpg_tem_jpg' 

# 함수 실행
convert_avif_to_jpg_batch_ultimate(input_directory, output_directory)