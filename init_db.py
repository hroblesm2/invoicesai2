# init_db.py
from app import init_app
from extensions import db
from models import Invoice, User, InvoiceSplit  # Importa todos tus modelos

def initialize_database():
    app = init_app()
    
    with app.app_context():
        print("Eliminando todas las tablas existentes...")
        db.drop_all()  # Esto borrará todas las tablas - ¡cuidado con los datos!
        
        print("Creando todas las tablas nuevas...")
        db.create_all()
        
        print("Base de datos inicializada correctamente!")
        
        # Verificar tablas creadas
        import sqlite3
        conn = sqlite3.connect('invoices.db')
        c = conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = c.fetchall()
        
        print("Tablas creadas:")
        for table in tables:
            print(f"- {table[0]}")
            
        conn.close()

if __name__ == "__main__":
    initialize_database()