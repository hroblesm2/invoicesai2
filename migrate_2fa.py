from app import init_app
from extensions import db
import sqlite3

def add_2fa_columns():
    app = init_app()
    
    with app.app_context():
        try:
            # Conexión directa a SQLite para añadir columnas
            conn = sqlite3.connect('invoices.db')
            cursor = conn.cursor()
            
            # Verificar si las columnas ya existen
            cursor.execute("PRAGMA table_info(user)")
            columns = [column[1] for column in cursor.fetchall()]
            
            # Añadir columnas si no existen
            if 'otp_secret' not in columns:
                cursor.execute("ALTER TABLE user ADD COLUMN otp_secret VARCHAR(32)")
                print("Columna 'otp_secret' añadida")
            
            if 'otp_enabled' not in columns:
                cursor.execute("ALTER TABLE user ADD COLUMN otp_enabled BOOLEAN DEFAULT 0")
                print("Columna 'otp_enabled' añadida")
            
            conn.commit()
            conn.close()
            
            print("Migración para 2FA completada con éxito")
            
        except Exception as e:
            print(f"Error durante la migración: {str(e)}")

if __name__ == "__main__":
    add_2fa_columns()