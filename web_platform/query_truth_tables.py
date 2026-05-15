import psycopg2

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
    cur.execute("SELECT id, question_text, options FROM neet_pyqs WHERE question_text ILIKE '%truth table is%' LIMIT 5;")
    rows = cur.fetchall()
    for row in rows:
        print("ID:", row[0])
        # print("TEXT:", row[1])
        print("OPTIONS:", row[2])
        print("---")
    conn.close()

if __name__ == "__main__":
    query()
