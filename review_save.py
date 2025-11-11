import pandas as pd
import mysql.connector
from mysql.connector import errorcode
import json
import os

# --- ⚙️ 데이터베이스 연결 설정 ---
DB_CONFIG = {
    'user': 'root',
    'password': '1234',
    'host': '127.0.0.1',
    'port': 3305,
    'database': 'aiproject'
}
TABLE_NAME = 'review'
CSV_FILE_PATH = 'review.csv'

# ⚠️ [필수 수정]: 실제 'review' 테이블의 컬럼 목록과 순서에 맞게 수정하세요.
DB_COLUMNS = [
    'review_id', 'product_id', 'rating', 'platform', 'review_date', 
    'review_text', 'review_images' 
]


# --- 💡 JSON 형식 필드 처리 함수 (필요한 경우) ---
def to_json_str(value):
    """NaN/None 값을 처리하고, Python 객체를 JSON 문자열로 변환합니다."""
    if pd.isna(value) or value is None:
        return None
    try:
        json.loads(value)
        return value
    except (TypeError, json.JSONDecodeError):
        # 유효한 JSON이 아니면 JSON 문자열로 덤프
        return json.dumps(value, ensure_ascii=False)


# --- 💾 데이터 삽입 함수 ---
def insert_data_to_mysql(df):
    """DataFrame의 데이터를 MySQL 테이블에 삽입합니다."""
    
    # 'image_urls', 'metadata' 등 JSON으로 저장될 컬럼 처리 (필요에 따라 수정/추가)
    json_cols = ['image_urls', 'metadata']
    for col in json_cols:
        if col in df.columns:
            df[col] = df[col].apply(to_json_str)

    # ✅ DB_COLUMNS 기준으로 최종 삽입할 컬럼만 필터링
    df_to_insert = df[[col for col in DB_COLUMNS if col in df.columns]].copy()

    conn = None
    cursor = None
    try:
        print(f"[{DB_CONFIG['database']}] 데이터베이스에 연결 중...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("✅ 연결 성공")

        # 삽입 쿼리에 사용할 컬럼 목록
        columns = ', '.join(df_to_insert.columns)
        placeholders = ', '.join(['%s'] * len(df_to_insert.columns))
        
        # INSERT ... ON DUPLICATE KEY UPDATE 쿼리 생성
        # review_id가 PRIMARY KEY 가정. 중복 시 content 필드 업데이트 예시
        update_cols = [f'{col}=VALUES({col})' for col in df_to_insert.columns if col not in ['review_id']]
        
        insert_query = f"""
            INSERT INTO {TABLE_NAME} ({columns}) 
            VALUES ({placeholders}) 
            ON DUPLICATE KEY UPDATE {', '.join(update_cols)}
        """

        total_rows = len(df_to_insert)
        print(f"총 {total_rows}개의 데이터를 삽입/업데이트합니다...")
        
        # NaN/None 값을 None으로 변환하여 MySQL에 NULL로 삽입되게 함
        data_to_insert = []
        for _, row in df_to_insert.iterrows():
            clean_row = [None if pd.isna(v) else v for v in row]
            data_to_insert.append(tuple(clean_row))

        cursor.executemany(insert_query, data_to_insert)
        
        conn.commit()
        print(f"✅ {cursor.rowcount}개의 레코드가 성공적으로 처리되었습니다.")

    except mysql.connector.Error as err:
        if conn:
            conn.rollback()
        print(f"❌ 데이터베이스 오류 ({err.errno}): {err.msg}")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ 예상치 못한 오류 발생: {e}")

    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()
            print("🔌 MySQL 연결 종료")


# --- 🚀 메인 실행 부분 ---
if __name__ == '__main__':
    if not os.path.exists(CSV_FILE_PATH):
        print(f"❌ 오류: 지정된 파일 경로에 '{CSV_FILE_PATH}' 파일이 없습니다. 경로를 확인하세요.")
    else:
        try:
            print(f"'{CSV_FILE_PATH}' 파일 읽는 중...")
            # 'cp949' 인코딩은 한글 CSV 파일에 흔히 사용됩니다.
            df = pd.read_csv(CSV_FILE_PATH, encoding='cp949')

            # ✅ 불필요한 열 제거
            df = df.loc[:, ~df.columns.isna()]
            df = df.loc[:, df.columns != 'nan']
            df = df.loc[:, ~df.columns.str.contains('^Unnamed', na=False)]
            
            # 💡 [필수]: review_date 컬럼이 있다면 DATE 형식으로 변환
            if 'review_date' in df.columns:
                df['review_date'] = pd.to_datetime(df['review_date'], errors='coerce').dt.date

            # 💡 [필수]: rating 및 helpful_count 컬럼 정수형 변환 (오류 방지)
            for col in ['rating', 'helpful_count']:
                if col in df.columns:
                    df[col] = df[col].astype(str).str.replace(r'[^\d.]', '', regex=True)
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    df[col] = df[col].fillna(0).astype('Int64').where(pd.notnull, None)


            # 최종 결측값 처리 (NaN을 None으로 변환)
            df = df.where(pd.notnull(df), None)

            # 최종 삽입 대상 컬럼 확인
            final_cols = [col for col in DB_COLUMNS if col in df.columns]
            print("CSV 데이터에서 추출된 최종 컬럼 목록:", final_cols)

            if df.empty or not final_cols:
                print("⚠️ 경고: 필터링 후 삽입할 데이터가 없거나 컬럼이 DB 컬럼 목록과 일치하지 않습니다.")
            else:
                insert_data_to_mysql(df)

        except FileNotFoundError:
            print(f"❌ 오류: '{CSV_FILE_PATH}' 파일을 찾을 수 없습니다.")
        except Exception as e:
            print(f"❌ 파일 처리 중 예상치 못한 오류 발생: {e}")