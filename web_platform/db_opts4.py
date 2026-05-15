import psycopg2

conn = psycopg2.connect(dbname='neet_db', user='postgres', password='Dream@1234', host='localhost')
cur = conn.cursor()
cur.execute("SELECT id, question_text FROM neet_pyqs WHERE question_text LIKE '%.png%' OR question_text LIKE '%.jpg%' LIMIT 5")
rows = cur.fetchall()
if rows:
    for r in rows:
        print("ID:", r[0], "Text snippet:", r[1][:200])
else:
    print("NO question_text contains .png or .jpg in the database.")
