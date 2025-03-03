# rebuild_sqlalchemy.py
from app import init_app
from extensions import db
from sqlalchemy import inspect

app = init_app()

with app.app_context():
    # Forzar a SQLAlchemy a refrescar sus metadatos
    inspector = inspect(db.engine)
    print("Forzando a SQLAlchemy a refrescar metadatos...")
    
    # Esto fuerza a SQLAlchemy a volver a cargar la información de la tabla
    db.metadata.clear()
    db.reflect()
    
    print("Metadatos actualizados. Tablas disponibles:")
    for table in inspector.get_table_names():
        print(f"- {table}")
        cols = [col['name'] for col in inspector.get_columns(table)]
        if 'user' in table.lower():
            print(f"  Columnas: {cols}")
    
    print("\nOperación completada. Reinicia la aplicación Flask.")