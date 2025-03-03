from app import init_app
from models import User, db

def create_admin_user():
    app = init_app()
    with app.app_context():
        # Verificar si ya existe un usuario admin
        admin = User.query.filter_by(username='admin').first()
        if admin is None:
            admin = User(
                username='admin',
                email='admin@example.com',
                role='admin'
            )
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("Usuario administrador creado exitosamente")
        else:
            print("El usuario administrador ya existe")

if __name__ == '__main__':
    create_admin_user()