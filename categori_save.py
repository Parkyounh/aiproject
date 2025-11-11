import pandas as pd
import mysql.connector
from mysql.connector import errorcode
import os

DB_CONFIG = {
    'user': 'root',
    'password': '1234',
    'host': '127.0.0.1',
    'port': 3305,
    'database': 'aiproject'
}

TABLE_NAME = 'categori'
CSV_FILE_PATH = 'categori.csv'

# DB_COLUMNS는 CSV 파일에서 추출되어 DB에 삽입될 컬럼의 순서를 정의합니다.
DB_COLUMNS = ['categori_id', 'major_categori', 'medium_categori', 'minor_categori', 'categori_url']

def insert_data_to_mysql(df):
    """DataFrame의 데이터를 MySQL 테이블에 삽입합니다."""
    
    # DB_COLUMNS에 있는 컬럼만 필터링하여 삽입용 DataFrame을 만듭니다.
    df_to_insert = df[[col for col in DB_COLUMNS if col in df.columns]].copy()

    conn = None
    cursor = None
    try:
        print(f"[{DB_CONFIG['database']}] 데이터베이스에 연결 중...")
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        print("✅ 연결 성공")

        # 삽입 쿼리에 사용할 컬럼 목록과 플레이스홀더를 df_to_insert 기준으로 생성
        columns = ', '.join(df_to_insert.columns)
        placeholders = ', '.join(['%s'] * len(df_to_insert.columns)) # df_to_insert 컬럼 개수만큼 %s 생성
        
        # INSERT ... ON DUPLICATE KEY UPDATE (PK: categori_id 가정)
        insert_query = f"""
            INSERT INTO {TABLE_NAME} ({columns})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE 
                major_categori=VALUES(major_categori),
                medium_categori=VALUES(medium_categori),
                minor_categori=VALUES(minor_categori),
                categori_url=VALUES(categori_url)
        """

        total_rows = len(df_to_insert)
        print(f"총 {total_rows}개의 데이터를 삽입/업데이트합니다...")

        # NaN/None 값을 None으로 변환 (MySQL NULL)
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

if __name__ == '__main__':
    if not os.path.exists(CSV_FILE_PATH):
        print(f"❌ 오류: 지정된 파일 경로에 '{CSV_FILE_PATH}' 파일이 없습니다. 경로를 확인하세요.")
    else:
        try:
            print(f"'{CSV_FILE_PATH}' 파일 읽는 중...")
            df = pd.read_csv(CSV_FILE_PATH, encoding='cp949')
            
            # 불필요한 열 제거
            df = df.loc[:, ~df.columns.isna()]
            df = df.loc[:, df.columns != 'nan']
            df = df.loc[:, ~df.columns.str.contains('^Unnamed', na=False)]

            # DB_COLUMNS 기준으로 필터링 (insert_data_to_mysql 함수에서 다시 수행하지만, 미리 확인)
            final_cols = [col for col in DB_COLUMNS if col in df.columns]
            df = df[final_cols]
            
            # 결측값 처리
            df = df.where(pd.notnull(df), None)

            print("CSV 데이터에서 추출된 최종 컬럼 목록:", final_cols)

            if df.empty:
                print("⚠️ 경고: 필터링 후 삽입할 데이터가 없습니다.")
            else:
                insert_data_to_mysql(df)

        except FileNotFoundError:
            print(f"❌ 오류: '{CSV_FILE_PATH}' 파일을 찾을 수 없습니다.")
        except Exception as e:
            print(f"❌ 파일 처리 중 예상치 못한 오류 발생: {e}")