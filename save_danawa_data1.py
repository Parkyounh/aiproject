import pandas as pd
from sqlalchemy import create_engine, text
import csv

# ----------------------------------------------------
# 📌 1. 데이터베이스 연결 설정 (수정 완료)
# ----------------------------------------------------
# 사용자 정보: root / 1234, 포트: 3305, 테이블: danawa_data1
# DB 이름은 사용하시는 데이터베이스 이름으로 변경해야 합니다. (예시: 'danawa_db')
DB_USER = "root"
DB_PASS = "1234"
DB_HOST = "localhost"
DB_PORT = "3305"
DB_NAME = "aiproject"
TABLE_NAME = "danawa_data1"
CSV_FILE = "danawa_유모차_output_final_cleaned_img_modified.csv"

# DB URL 구성: 'mysql+mysqlconnector://사용자명:비밀번호@호스트:포트/DB이름'
DB_URL = f"mysql+mysqlconnector://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"


# ----------------------------------------------------
# 📌 2. CSV 파일 로드 및 컬럼명 일치 작업
# ----------------------------------------------------
try:
    # CSV 파일 로드 (저장 시 사용했던 quoting 옵션을 고려)
    df = pd.read_csv(CSV_FILE, encoding="utf-8-sig", quoting=csv.QUOTE_ALL)
    print(f"✅ CSV 파일 '{CSV_FILE}' 로드 완료. (총 {len(df)} 행)")

    # SQL 테이블 컬럼명 (pcode, name, url, image, min, max, price_trend, details)에 맞게 컬럼명 수정
    df.columns = [
        'pcode', 'name', 'url', 'image', 'min', 'max', 
        'price_trend', 'details' 
    ]
    
    print("✅ DataFrame 컬럼명 변경 완료.")

# ----------------------------------------------------
# 📌 3. 데이터베이스 연결 및 저장
# ----------------------------------------------------
    # 데이터베이스 엔진 생성
    engine = create_engine(DB_URL)
    
    # 데이터를 DB 테이블에 저장
    # if_exists='append': 기존 데이터가 있으면 추가합니다.
    # index=False: DataFrame 인덱스를 테이블에 저장하지 않습니다.
    
    # JSON 컬럼을 VARCHAR(LONGTEXT)로 전송 후 MySQL에서 JSON으로 변환 (MySQL to_sql의 JSON 타입 처리 문제 회피)
    df.to_sql(
        TABLE_NAME, 
        engine, 
        if_exists='append', # 데이터를 추가 (replace 대신 append 사용)
        index=False,
        chunksize=1000
    )

    print(f"🎉 데이터베이스 저장 성공: {TABLE_NAME} 테이블에 {len(df)}개 행이 삽입되었습니다.")
    
    # 💡 데이터 타입 조정: JSON 문자열을 MySQL의 JSON 타입으로 변환
    # VARCHAR로 들어간 price_trend와 details를 JSON 타입으로 변경하는 SQL 명령어
    with engine.connect() as connection:
        update_price_trend_sql = text(f"ALTER TABLE {TABLE_NAME} MODIFY COLUMN price_trend JSON NULL")
        update_details_sql = text(f"ALTER TABLE {TABLE_NAME} MODIFY COLUMN details JSON NULL")
        connection.execute(update_price_trend_sql)
        connection.execute(update_details_sql)
        connection.commit()
        print("✅ price_trend와 details 컬럼을 JSON 타입으로 변경 완료.")


except FileNotFoundError:
    print(f"❌ 오류: CSV 파일 '{CSV_FILE}'을 찾을 수 없습니다. 경로를 확인해주세요.")
except Exception as e:
    print(f"❌ 데이터베이스 연결 또는 저장 중 오류 발생. DB_URL과 접속 정보를 확인하세요.: {e}")