import psycopg2

def create_db_connection():
    conn = psycopg2.connect(
        host='localhost',
        database='mail_app',
        user='postgres',
        password='password'
    )
    return conn
