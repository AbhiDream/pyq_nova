import psycopg2
conn = psycopg2.connect(host='127.0.0.1', dbname='neet_db', user='postgres', password='Dream@1234', port='5432')
cur = conn.cursor()

# Check columns in neet_pyqs
cur.execute("""
    SELECT column_name, data_type 
    FROM information_schema.columns 
    WHERE table_name = 'neet_pyqs' 
    ORDER BY ordinal_position
""")
print("=== COLUMNS ===")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Sample a few missing-solution rows to see what fields are available
print("\n=== SAMPLE MISSING SOLUTION ROWS ===")
cur.execute("""
    SELECT id, year, subject, chapter, question_text
    FROM neet_pyqs
    WHERE solution IS NULL OR TRIM(solution) = ''
    ORDER BY year DESC
    LIMIT 5
""")
for row in cur.fetchall():
    print(f"  id={row[0]}, year={row[1]}, subject={row[2]}, chapter={row[3]}")
    print(f"  Q: {repr(row[4][:60])}")
    print()

conn.close()
