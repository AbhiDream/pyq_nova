import psycopg2
import json

conn_params = {
    "dbname": "neet_db",
    "user": "postgres",
    "password": "Dream@1234",
    "host": "127.0.0.1",
    "port": "5432"
}

def query():
    conn = psycopg2.connect(**conn_params)
    cur = conn.cursor()
    cur.execute("SELECT id, question_text, image_path, options, options_image FROM neet_pyqs WHERE question_text ILIKE '%circuit shown below%' LIMIT 5;")
    rows = cur.fetchall()
    for row in rows:
        print("ID:", row[0])
        print("TEXT:", row[1])
        print("IMAGE_PATH:", row[2])
        print("OPTIONS_IMAGE:", row[4])
        print("OPTIONS:", row[3])
        print("---")
    conn.close()

if __name__ == "__main__":
    query()
