# weaviate_to_mysql_with_clear.py
# Weaviate DB의 데이터를 MySQL로 마이그레이션하기 전에 테이블을 초기화합니다.

import sys
import time
import json
import mysql.connector
from weaviate.classes.query import MetadataQuery

# utils.py에서 정의된 함수/변수 임포트 (이 파일은 로컬 환경에 맞게 정의되어 있어야 합니다)
from utils import connect_to_weaviate, WEAVIATE_CLASS_NAME 

# -----------------------------------------------------------
# 1. MySQL 연결 설정
# -----------------------------------------------------------
MYSQL_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'aiproject',
    'port': 3305 
}

TABLE_NAME = "product_vectors"

# -----------------------------------------------------------
# 2. MySQL 연결 함수
# -----------------------------------------------------------
def connect_to_mysql():
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"❌ MySQL 연결 실패: {err}")
        sys.exit()

# -----------------------------------------------------------
# 3. MySQL 테이블 초기화 함수 (TRUNCATE)
# -----------------------------------------------------------
def clear_mysql_table(conn):
    """지정된 테이블의 모든 데이터를 삭제하여 초기화합니다."""
    cursor = conn.cursor()
    # TRUNCATE TABLE은 DELETE FROM보다 빠르고 효율적입니다.
    sql = f"TRUNCATE TABLE {TABLE_NAME};" 
    print(f"\n🧹 MySQL 테이블 '{TABLE_NAME}' 초기화 중...")
    
    try:
        cursor.execute(sql)
        conn.commit()
        print("✅ 테이블 초기화 완료.")
    except mysql.connector.Error as err:
        print(f"❌ 테이블 초기화 실패: {err}")
        # 초기화 실패 시 롤백 (만약을 대비)
        conn.rollback() 
    finally:
        cursor.close()

# -----------------------------------------------------------
# 4. 데이터 마이그레이션 실행
# -----------------------------------------------------------
print(f"\n🔄 Weaviate to MySQL 마이그레이션 시작...")
start_time = time.time()
total_migrated = 0

# Weaviate 연결
try:
    wv_client = connect_to_weaviate()
    wv_collection = wv_client.collections.get(WEAVIATE_CLASS_NAME)
except Exception as e:
    print(f"❌ Weaviate 연결 실패: {e}")
    sys.exit()

# MySQL 연결
mysql_conn = connect_to_mysql()
# 📌 마이그레이션 시작 전 테이블 초기화
clear_mysql_table(mysql_conn) 
mysql_cursor = mysql_conn.cursor()


try:
    # 📌 Weaviate의 모든 객체를 벡터를 포함하여 순회합니다.
    print(f"🔍 Weaviate에서 데이터 조회 및 삽입 시작...")
    
    for obj in wv_collection.iterator(include_vector=True):
        
        # Weaviate 데이터 추출
        properties = obj.properties
        uuid = str(obj.uuid)
        vector_data = obj.vector.get('default') 

        # MySQL에 삽입할 데이터 준비
        product_id = properties.get("product_id")
        image_path = properties.get("imagePath")
        
        if vector_data is not None:
            image_vector_json = json.dumps(vector_data) 
        else:
            image_vector_json = None

        # MySQL 삽입 쿼리 (UUID를 PRIMARY KEY로 사용)
        sql = f"""
        INSERT INTO {TABLE_NAME} 
        (product_id, image_path, image_vector, weaviate_uuid)
        VALUES (%s, %s, %s, %s);
        """
        
        # 쿼리 실행
        data = (product_id, image_path, image_vector_json, uuid)
        mysql_cursor.execute(sql, data)
        
        total_migrated += 1
        if total_migrated % 100 == 0:
            mysql_conn.commit()
            print(f"   ... {total_migrated}개 객체 커밋됨.")
            
    # 최종 커밋
    mysql_conn.commit()
    end_time = time.time()
    
    print(f"\n✅ 마이그레이션 완료! 총 {total_migrated}개 객체를 {end_time - start_time:.4f}초 만에 옮겼습니다.")

except Exception as e:
    print(f"\n❌ 데이터 마이그레이션 중 오류 발생: {e}")
    mysql_conn.rollback() 

finally:
    # 연결 종료
    mysql_cursor.close()
    mysql_conn.close()
    wv_client.close()
    print("👋 모든 DB 연결 종료.")