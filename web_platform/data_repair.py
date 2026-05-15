import psycopg2
import re
import json

# DB Connection Config
conn_params = {
    "dbname": "neet_db",
    "user": "postgres",
    "password": "Dream@1234", # <--- Apna password yahan daalein
    "host": "127.0.0.1",
    "port": "5432"
}

def repair_database():
    try:
        conn = psycopg2.connect(**conn_params)
        cur = conn.cursor()
        
        # 1. Fetch all questions that have <img> tags in their text
        print("🔍 Scanning database for merged images...")
        cur.execute("SELECT id, question_text, options FROM neet_pyqs WHERE question_text LIKE '%<img%';")
        rows = cur.fetchall()
        print(f"📦 Found {len(rows)} questions to repair.")

        for row in rows:
            q_id, raw_text, existing_options = row
            
            # 2. Extract all image sources from <img> tags using Regex
            # Pattern dhundega src="filename.png" ya src='filename.png'
            img_sources = re.findall(r'<img [^>]*src=["\']([^"\']+)["\']', raw_text)
            
            if not img_sources:
                continue

            # 3. Cleanup: Remove <img> tags from the text
            clean_text = re.sub(r'<img [^>]*>', '', raw_text).strip()
            
            # 4. Logic: First image goes to image_path, others to Options
            main_image = img_sources[0]
            other_images = img_sources[1:] # Baaki bachi hui images
            
            # Options Mapping (A, B, C, D)
            new_options = {}
            if other_images:
                keys = ['A', 'B', 'C', 'D']
                for i, img in enumerate(other_images):
                    if i < len(keys):
                        new_options[keys[i]] = img
            else:
                # Agar sirf ek hi image hai, toh options purane hi rakhein
                new_options = existing_options if existing_options else {}

            # 5. Update the Database
            update_query = """
                UPDATE neet_pyqs 
                SET question_text = %s, 
                    image_path = %s, 
                    options = %s 
                WHERE id = %s
            """
            cur.execute(update_query, (
                clean_text, 
                main_image, 
                json.dumps(new_options) if new_options else None, 
                q_id
            ))

        conn.commit()
        print(f"✅ Successfully repaired {len(rows)} questions!")

    except Exception as e:
        print(f"❌ Error during repair: {e}")
        if conn: conn.rollback()
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    repair_database()