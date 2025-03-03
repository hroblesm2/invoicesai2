from flask_wtf import FlaskForm
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (StringField, SubmitField, SelectField, 
                    DecimalField, DateField, TextAreaField,
                    PasswordField, BooleanField, IntegerField)
from wtforms.validators import DataRequired, Optional, Email

class UserCreateForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    role = SelectField('Rol', choices=[('admin', 'Administrador'), ('asesor', 'Asesor')],
                      validators=[DataRequired()])
    estudio = SelectField('Estudio', choices=[
        ('', 'Seleccionar...'),
        ('estudio_bedoya', 'Estudio Bedoya'),
        ('estudio_angobaldo', 'Estudio Angobaldo'),
        ('estudio_suluaga', 'Estudio Suluaga'),
        ('estudio_echecopar', 'Estudio Echecopar')
    ])
    submit = SubmitField('Crear Usuario')

class UploadForm(FlaskForm):
    upload_type = SelectField('Tipo de Carga', 
                            choices=[('single', 'Documento Individual'), 
                                   ('batch', 'Carga Masiva')],
                            default='single')
    invoice = FileField('Seleccionar Documento', 
                       validators=[
                           FileAllowed(['pdf', 'png', 'jpg', 'jpeg'], 'Solo se permiten PDF e imágenes.')
                       ])
    batch_files = FileField('Seleccionar Documentos',
                          validators=[
                              FileAllowed(['pdf', 'png', 'jpg', 'jpeg'], 'Solo se permiten PDF e imágenes.')
                          ])
    submit = SubmitField('Procesar')

class SearchForm(FlaskForm):
    search_query = StringField('Buscar', render_kw={"placeholder": "Buscar por proveedor..."})
    date_from = DateField('Fecha Desde', format='%Y-%m-%d', validators=[Optional()])
    date_to = DateField('Fecha Hasta', format='%Y-%m-%d', validators=[Optional()])
    amount_min = DecimalField('Monto Mínimo', validators=[Optional()])
    amount_max = DecimalField('Monto Máximo', validators=[Optional()])

class EditInvoiceForm(FlaskForm):
    vendor = StringField('Proveedor', validators=[DataRequired()])
    invoice_number = StringField('Número de Factura')
    total = StringField('Total', validators=[DataRequired()])
    date = StringField('Fecha', validators=[DataRequired()])
    vendor_address = StringField('Dirección del Proveedor')
    items = TextAreaField('Productos/Servicios')
    tax = StringField('Impuestos')
    payment_method = SelectField('Método de Pago',
                               choices=[('', 'Seleccionar...'),
                                      ('efectivo', 'Efectivo'),
                                      ('transferencia', 'Transferencia'),
                                      ('tarjeta', 'Tarjeta'),
                                      ('cheque', 'Cheque')])
    submit = SubmitField('Guardar Cambios')
    
class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recordarme')
    submit = SubmitField('Iniciar Sesión')
    
class InvoiceSplitForm(FlaskForm):
    is_splittable = BooleanField('Dividir Factura')
    num_obligations = IntegerField('Número de Obligaciones', 
                                 validators=[Optional()],
                                 default=1)
    submit = SubmitField('Guardar')

class OTPVerificationForm(FlaskForm):
    otp_token = StringField('Código de verificación', validators=[DataRequired()])
    submit = SubmitField('Verificar')

class EnableOTPForm(FlaskForm):
    otp_token = StringField('Código de verificación', validators=[DataRequired()])
    submit = SubmitField('Activar autenticación de dos factores')
    
class DisableOTPForm(FlaskForm):
    otp_token = StringField('Código de verificación', validators=[DataRequired()])
    submit = SubmitField('Desactivar autenticación de dos factores')