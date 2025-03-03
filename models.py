from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from extensions import db

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(120), nullable=False)
    vendor = db.Column(db.String(120))
    total = db.Column(db.String(50))
    date = db.Column(db.String(50))
    invoice_number = db.Column(db.String(50))
    vendor_address = db.Column(db.String(200))
    items = db.Column(db.Text)  # Almacenará JSON de productos/servicios
    tax = db.Column(db.String(50))
    payment_method = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_splittable = db.Column(db.Boolean, default=False)
    num_obligations = db.Column(db.Integer, default=1)
    split_status = db.Column(db.String(20), default='no_split') 
    otp_secret = db.Column(db.String(32)) #Secreto para generar codigos OTP
    otp_enabled = db.Column(db.Boolean, default=False) #Si el 2FA está activado
        
    def __repr__(self):
        return f'<Invoice {self.id} - {self.vendor}>'
    
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), nullable=False, default='asesor')
    estudio = db.Column(db.String(50))  # Nuevo campo
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    otp_secret = db.Column(db.String(32))
    otp_enabled = db.Column(db.Boolean, default=False)
    
    def get_totp_uri(self):
        """"Generamos la URI para el código QR de Google Authenticator"""
        import pyotp
        if self.otp_secret:
            return pyotp.totp.TOTP(self.otp_secret).provisioning_uri(
                name=self.email,
                issuer_name='GPS Asset Management'
            )
        return None
        
    def verify_totp(self, token):
        """Verifica un token TOTP"""
        import pyotp
        if self.otp_secret and token:  
           totp = pyotp.TOTP(self.otp_secret)  
           return totp.verify(token)
        return False
        
    def generate_otp_secret(self):
        """Genera un nuevo secreto TOTP"""
        import pyotp
        self.otp_secret = pyotp.random_base32()
        return self.otp_secret
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def __repr__(self):
        return f'<User {self.username}>'

class InvoiceSplit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    obligation_number = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    invoice = db.relationship('Invoice', backref=db.backref('splits', lazy=True))