import psycopg2

conn = psycopg2.connect(dbname='neet_db', user='postgres', password='Dream@1234', host='localhost')
cur = conn.cursor()
cur.execute("SELECT id, options FROM neet_pyqs WHERE options::text LIKE '%.png%' OR options::text LIKE '%.jpg%' LIMIT 5")
rows = cur.fetchall()
if rows:
    for r in rows:
        print("ID:", r[0], "Opts:", r[1])
else:
    print("NO options contain .png or .jpg in the database.")
