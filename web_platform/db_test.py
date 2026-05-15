import psycopg2
conn=psycopg2.connect(dbname='neet_db', user='postgres', password='Dream@1234', host='localhost')
cur=conn.cursor()
cur.execute("SELECT image_path FROM neet_pyqs WHERE image_path IS NOT NULL AND image_path != '' AND image_path != 'None' LIMIT 5")
print(cur.fetchall())
