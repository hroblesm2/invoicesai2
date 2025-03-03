# Crear un script Python (update_db.py)
from app import init_app
from extensions import db
import sqlite3

app = init_app()

with app.app_context():
    conn = sqlite3.connect('invoices.db')
    c = conn.cursor()
    
    # Añadir las columnas faltantes
    try:
        c.execute('ALTER TABLE invoice ADD COLUMN is_splittable BOOLEAN DEFAULT 0')
        c.execute('ALTER TABLE invoice ADD COLUMN num_obligations INTEGER DEFAULT 1')
        c.execute('ALTER TABLE invoice ADD COLUMN split_status VARCHAR(20) DEFAULT "no_split"')
        conn.commit()
        print("Columnas añadidas correctamente")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")
    
    conn.close()