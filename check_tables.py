# check_tables.py
import sqlite3

def check_database_tables():
    conn = sqlite3.connect('invoices.db')
    cursor = conn.cursor()
    
    # Listar todas las tablas en la base de datos
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Tablas en la base de datos:")
    for table in tables:
        print(f"- {table[0]}")
        
        # Si encontramos una tabla que podría ser la de usuarios, mostramos su estructura
        if 'user' in table[0].lower():
            print(f"\nEstructura de la tabla {table[0]}:")
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            for column in columns:
                print(f"  - {column[1]} ({column[2]})")
    
    conn.close()

if __name__ == "__main__":
    check_database_tables()