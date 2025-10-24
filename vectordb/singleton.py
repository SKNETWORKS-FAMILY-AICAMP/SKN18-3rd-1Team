import psycopg2 
from psycopg2 import pool 


def singleton(class_):
    instances = {}  # 각 클래스별로 이미 생성된 인스턴스를 저장해두는 역할
    
    # class_의 인스턴스가 있는지 확인
    def get_instance(*args, **kwargs):
        if class_ not in instances:
            instances[class_] = class_(*args, **kwargs)
        return instances[class_]

    return get_instance


@singleton
class SingletonDatabase:
    _connection_pool = None
    
    def __init__(self, db_config):
        # 이미 풀 초기화가 되어 있으면 재설정 안 함
        if self._connection_pool is None:
            self._connection_pool = psycopg2.pool.SimpleConnectionPool(
                minconn=1,
                maxconn=5,
                **db_config
            )
            print("✅ PostgreSQL 연결 풀 생성 완료")
            
    def get_connection(self):
        return self._connection_pool.getconn()

    def release_connection(self, conn):
        self._connection_pool.putconn(conn)
    
    def close_all(self):
        if self._connection_pool:
            self._connection_pool.closeall()
            self._connection_pool = None
        print("🔒 모든 연결 종료 완료")