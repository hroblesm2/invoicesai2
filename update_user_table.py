# update_user_table.py (modificado)
import sqlite3

def update_user_table():
    # Conectarse a la base de datos
    conn = sqlite3.connect('invoices.db')
    cursor = conn.cursor()
    
    # Listar tablas para encontrar la tabla de usuarios
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [table[0] for table in cursor.fetchall()]
    
    print("Tablas existentes:", tables)
    
    # Buscar la tabla de usuarios (podría ser 'user', 'users', etc.)
    user_table = None
    for table in tables:
        if 'user' in table.lower():
            user_table = table
            break
    
    if not user_table:
        print("No se encontró una tabla de usuarios en la base de datos.")
        print("Creando tabla 'user'...")
        
        # Crear la tabla si no existe
        cursor.execute("""
        CREATE TABLE user (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            role TEXT DEFAULT 'asesor',
            estudio TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            otp_secret TEXT,
            otp_enabled INTEGER DEFAULT 0
        );
        """)
        user_table = 'user'
        print(f"Tabla '{user_table}' creada correctamente.")
    else:
        print(f"Se encontró la tabla de usuarios: '{user_table}'")
    
    # Verificar si las columnas ya existen
    cursor.execute(f"PRAGMA table_info({user_table})")
    columns = [column[1] for column in cursor.fetchall()]
    print(f"Columnas existentes en {user_table}:", columns)
    
    # Añadir columnas si no existen
    try:
        if 'otp_secret' not in columns:
            cursor.execute(f"ALTER TABLE {user_table} ADD COLUMN otp_secret TEXT")
            print(f"Columna 'otp_secret' añadida a {user_table}")
        
        if 'otp_enabled' not in columns:
            cursor.execute(f"ALTER TABLE {user_table} ADD COLUMN otp_enabled INTEGER DEFAULT 0")
            print(f"Columna 'otp_enabled' añadida a {user_table}")
        
        conn.commit()
        print(f"Tabla {user_table} actualizada correctamente")
    except Exception as e:
        print(f"Error al actualizar la tabla: {e}")
    
    conn.close()

if __name__ == "__main__":
    update_user_table()