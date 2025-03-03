import os
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, send_from_directory
from werkzeug.utils import secure_filename
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from extensions import db
from models import Invoice, User  # Agregamos User aquí
from forms import UploadForm, SearchForm, EditInvoiceForm, LoginForm  # Agregamos LoginForm
from config import Config
import csv
import io
from datetime import datetime
from sqlalchemy import Float, cast, and_, or_, func
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from functools import wraps
from flask_migrate import Migrate
from urllib.parse import urlparse  # Este es el nuevo import que reemplaza a werkzeug.urls
from wtforms.validators import DataRequired, Optional, Email
from forms import (UploadForm, SearchForm, EditInvoiceForm, 
                  LoginForm, UserCreateForm, EnableOTPForm, DisableOTPForm, OTPVerificationForm)

try:
    import xlsxwriter
    EXCEL_ENABLED = True
except ImportError:
    EXCEL_ENABLED = False
    print("XlsxWriter no está disponible, la exportación a Excel estará deshabilitada")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    db.init_app(app)
    migrate = Migrate(app, db)
    
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor inicie sesión para acceder a esta página.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))
    
    document_analysis_client = DocumentAnalysisClient(
        endpoint=app.config['AZURE_ENDPOINT'],
        credential=AzureKeyCredential(app.config['AZURE_KEY'])
    )

    def allowed_file(filename):
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

    @app.route('/', methods=['GET', 'POST'])
    @login_required
    def index():
        form = UploadForm()
        if form.validate_on_submit():
            if form.upload_type.data == 'single':
                file = form.invoice.data
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    file.save(filepath)

                    try:
                        with open(filepath, "rb") as f:
                            poller = document_analysis_client.begin_analyze_document(
                                "prebuilt-invoice", 
                                document=f
                            )
                            result = poller.result()

                        extracted_data = {
                            'vendor': '',
                            'total': '',
                            'date': '',
                            'invoice_number': '',
                            'vendor_address': '',
                            'items': '',
                            'tax': '',
                            'payment_method': ''
                        }

                        if hasattr(result, 'documents') and len(result.documents) > 0:
                            doc = result.documents[0]
                            fields = doc.fields

                            if 'VendorName' in fields:
                                extracted_data['vendor'] = fields['VendorName'].value if fields['VendorName'].value else ""
                            if 'InvoiceTotal' in fields:
                                extracted_data['total'] = str(fields['InvoiceTotal'].value) if fields['InvoiceTotal'].value else ""
                            if 'InvoiceDate' in fields:
                                extracted_data['date'] = str(fields['InvoiceDate'].value) if fields['InvoiceDate'].value else ""
                            if 'InvoiceId' in fields:
                                extracted_data['invoice_number'] = str(fields['InvoiceId'].value) if fields['InvoiceId'].value else ""

                            # Procesamiento de la dirección
                            if 'VendorAddress' in fields:
                                address_value = fields['VendorAddress'].value
                                if address_value:
                                    try:
                                        address_parts = []
                                        
                                        if hasattr(address_value, 'street_address') and address_value.street_address:
                                            address_parts.append(str(address_value.street_address))
                                        elif hasattr(address_value, 'house_number') and hasattr(address_value, 'road'):
                                            if address_value.house_number:
                                                address_parts.append(str(address_value.house_number))
                                            if address_value.road:
                                                address_parts.append(str(address_value.road))
                                        
                                        if hasattr(address_value, 'city') and address_value.city:
                                            address_parts.append(str(address_value.city))
                                        if hasattr(address_value, 'state') and address_value.state:
                                            address_parts.append(str(address_value.state))
                                        if hasattr(address_value, 'country_region') and address_value.country_region:
                                            address_parts.append(str(address_value.country_region))
                                        
                                        formatted_address = ', '.join(filter(None, address_parts))
                                        extracted_data['vendor_address'] = formatted_address if formatted_address else ""
                                    except Exception as e:
                                        print(f"Error procesando dirección: {str(e)}")
                                        extracted_data['vendor_address'] = str(address_value)
                                else:
                                    extracted_data['vendor_address'] = ""

                            # Procesamiento de items
                            # Procesamiento de items
                            if 'Items' in fields:
                                items_value = fields['Items'].value
                                if items_value:
                                    try:
                                        # Si es un solo item
                                        if isinstance(items_value, dict) and 'Description' in items_value:
                                            # Extraer directamente la descripción del item
                                            description = items_value['Description']
                                            extracted_data['items'] = description.value if hasattr(description, 'value') else str(description)
                                        
                                        # Si es una lista de items
                                        elif isinstance(items_value, list):
                                            descriptions = []
                                            for item in items_value:
                                                if isinstance(item, dict) and 'Description' in item:
                                                    desc = item['Description']
                                                    if hasattr(desc, 'value'):
                                                        descriptions.append(desc.value)
                                                    else:
                                                        descriptions.append(str(desc))
                                            extracted_data['items'] = "; ".join(filter(None, descriptions))
                                        
                                        # Si es un DocumentField
                                        elif hasattr(items_value, 'value') and isinstance(items_value.value, dict):
                                            if 'Description' in items_value.value:
                                                desc = items_value.value['Description']
                                                if hasattr(desc, 'value'):
                                                    extracted_data['items'] = desc.value
                                                else:
                                                    extracted_data['items'] = str(desc)
                                        else:
                                            # Si no podemos extraer la descripción, usar el contenido
                                            if hasattr(items_value, 'content'):
                                                extracted_data['items'] = items_value.content
                                            else:
                                                extracted_data['items'] = str(items_value)

                                    except Exception as e:
                                        print(f"Error procesando items: {str(e)}")
                                        extracted_data['items'] = "Error al procesar items"
                                else:
                                    extracted_data['items'] = ""
                                    
                            if 'TotalTax' in fields:
                                extracted_data['tax'] = str(fields['TotalTax'].value) if fields['TotalTax'].value else ""
                            if 'PaymentMethod' in fields:
                                extracted_data['payment_method'] = fields['PaymentMethod'].value if fields['PaymentMethod'].value else ""

                        new_invoice = Invoice(
                            filename=filename,
                            vendor=extracted_data['vendor'],
                            total=extracted_data['total'],
                            date=extracted_data['date'],
                            invoice_number=extracted_data['invoice_number'],
                            vendor_address=extracted_data['vendor_address'],
                            items=extracted_data['items'],
                            tax=extracted_data['tax'],
                            payment_method=extracted_data['payment_method']
                        )
                        db.session.add(new_invoice)
                        db.session.commit()

                        flash('Documento procesado exitosamente!', 'success')
                        preview_url = url_for('uploaded_file', filename=filename)
                        
                        return render_template('index.html', 
                                            form=form,
                                            preview_url=preview_url,
                                            extracted_data=extracted_data)

                    except Exception as e:
                        flash(f'Error al procesar el documento: {str(e)}', 'danger')
                        return redirect(url_for('index'))

            elif form.upload_type.data == 'batch':
                files = request.files.getlist('batch_files')
                processed = 0
                errors = 0
                
                if not files:
                    flash('No se seleccionaron archivos', 'warning')
                    return redirect(url_for('index'))
                
                for file in files:
                    if file and allowed_file(file.filename):
                        try:
                            filename = secure_filename(file.filename)
                            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                            file.save(filepath)

                            with open(filepath, "rb") as f:
                                poller = document_analysis_client.begin_analyze_document(
                                    "prebuilt-invoice", 
                                    document=f
                                )
                                result = poller.result()

                            extracted_data = {
                                'vendor': '',
                                'total': '',
                                'date': '',
                                'invoice_number': '',
                                'vendor_address': '',
                                'items': '',
                                'tax': '',
                                'payment_method': ''
                            }

                            if hasattr(result, 'documents') and len(result.documents) > 0:
                                doc = result.documents[0]
                                fields = doc.fields

                                if 'VendorName' in fields:
                                    extracted_data['vendor'] = fields['VendorName'].value if fields['VendorName'].value else ""
                                if 'InvoiceTotal' in fields:
                                    extracted_data['total'] = str(fields['InvoiceTotal'].value) if fields['InvoiceTotal'].value else ""
                                if 'InvoiceDate' in fields:
                                    extracted_data['date'] = str(fields['InvoiceDate'].value) if fields['InvoiceDate'].value else ""
                                if 'InvoiceId' in fields:
                                    extracted_data['invoice_number'] = str(fields['InvoiceId'].value) if fields['InvoiceId'].value else ""

                                # Procesamiento de la dirección
                                if 'VendorAddress' in fields:
                                    address_value = fields['VendorAddress'].value
                                    if address_value:
                                        try:
                                            address_parts = []
                                            
                                            if hasattr(address_value, 'street_address') and address_value.street_address:
                                                address_parts.append(str(address_value.street_address))
                                            elif hasattr(address_value, 'house_number') and hasattr(address_value, 'road'):
                                                if address_value.house_number:
                                                    address_parts.append(str(address_value.house_number))
                                                if address_value.road:
                                                    address_parts.append(str(address_value.road))
                                            
                                            if hasattr(address_value, 'city') and address_value.city:
                                                address_parts.append(str(address_value.city))
                                            if hasattr(address_value, 'state') and address_value.state:
                                                address_parts.append(str(address_value.state))
                                            if hasattr(address_value, 'country_region') and address_value.country_region:
                                                address_parts.append(str(address_value.country_region))
                                            
                                            formatted_address = ', '.join(filter(None, address_parts))
                                            extracted_data['vendor_address'] = formatted_address if formatted_address else ""
                                        except Exception as e:
                                            print(f"Error procesando dirección: {str(e)}")
                                            extracted_data['vendor_address'] = str(address_value)
                                    else:
                                        extracted_data['vendor_address'] = ""

                                # Procesamiento de items
                                if 'Items' in fields:
                                    items_value = fields['Items'].value
                                    if items_value:
                                        try:
                                            if isinstance(items_value, list):
                                                # Para múltiples items
                                                items_descriptions = []
                                                for item in items_value:
                                                    if isinstance(item, dict) and 'Description' in item:
                                                        if hasattr(item['Description'], 'value'):
                                                            items_descriptions.append(str(item['Description'].value))
                                                        else:
                                                            items_descriptions.append(str(item['Description']))
                                                    elif isinstance(item, dict):
                                                        # Si no hay Description pero hay otros campos
                                                        desc_parts = []
                                                        if 'Quantity' in item:
                                                            qty = item['Quantity'].value if hasattr(item['Quantity'], 'value') else item['Quantity']
                                                            desc_parts.append(f"Cantidad: {qty}")
                                                        if 'Description' in item:
                                                            desc = item['Description'].value if hasattr(item['Description'], 'value') else item['Description']
                                                            desc_parts.append(str(desc))
                                                        if desc_parts:
                                                            items_descriptions.append(" - ".join(desc_parts))
                                                extracted_data['items'] = "; ".join(items_descriptions)
                                            else:
                                                # Para un solo item
                                                if hasattr(items_value, 'value') and isinstance(items_value.value, dict):
                                                    if 'Description' in items_value.value:
                                                        desc = items_value.value['Description']
                                                        extracted_data['items'] = str(desc.value if hasattr(desc, 'value') else desc)
                                                    else:
                                                        extracted_data['items'] = str(items_value.value)
                                                else:
                                                    extracted_data['items'] = str(items_value)
                                        except Exception as e:
                                            print(f"Error procesando items: {str(e)}")
                                            # En caso de error, guardar una versión simplificada
                                            try:
                                                if hasattr(items_value, 'content'):
                                                    extracted_data['items'] = items_value.content
                                                else:
                                                    extracted_data['items'] = "Error al procesar items"
                                            except:
                                                extracted_data['items'] = "Error al procesar items"
                                    else:
                                        extracted_data['items'] = ""
                                        
                                if 'TotalTax' in fields:
                                    extracted_data['tax'] = str(fields['TotalTax'].value) if fields['TotalTax'].value else ""
                                if 'PaymentMethod' in fields:
                                    extracted_data['payment_method'] = fields['PaymentMethod'].value if fields['PaymentMethod'].value else ""

                                new_invoice = Invoice(
                                    filename=filename,
                                    vendor=extracted_data['vendor'],
                                    total=extracted_data['total'],
                                    date=extracted_data['date'],
                                    invoice_number=extracted_data['invoice_number'],
                                    vendor_address=extracted_data['vendor_address'],
                                    items=extracted_data['items'],
                                    tax=extracted_data['tax'],
                                    payment_method=extracted_data['payment_method']
                                )
                                db.session.add(new_invoice)
                                processed += 1

                        except Exception as e:
                            errors += 1
                            print(f"Error procesando {file.filename}: {str(e)}")

                if processed > 0:
                    try:
                        db.session.commit()
                        flash(f'Se procesaron {processed} documentos exitosamente. Errores: {errors}', 'success')
                    except Exception as e:
                        db.session.rollback()
                        flash(f'Error al guardar en la base de datos: {str(e)}', 'danger')
                else:
                    flash('No se pudo procesar ningún documento', 'danger')

                return redirect(url_for('history'))

        return render_template('index.html', form=form)
    
    @app.route('/uploads/<filename>')
    @login_required
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    
    @app.route('/invoice/<int:id>/split', methods=['GET', 'POST'])
    @login_required
    def split_invoice(id):
        invoice = Invoice.query.get_or_404(id)
        form = InvoiceSplitForm()
        
        if form.validate_on_submit():
            invoice.is_splittable = form.is_splittable.data
            if invoice.is_splittable:
                invoice.num_obligations = form.num_obligations.data
                invoice.split_status = 'pending'
            else:
                invoice.num_obligations = 1
                invoice.split_status = 'no_split'
            
            db.session.commit()
            
            if invoice.is_splittable:
                handler = InvoiceSplitService(invoice)
                handler.create_splits()
                
            db.session.commit()
            
            if invoices.is_splittable:
                handler = InvoiceSplitHandler(invoice)
                handler.create_splits()
            
            flash('Factura dividida exitosamente!', 'success')
            return redirect(url_for('invoices_details', id=invoice.id))
        
        form.is_splittable.data = invoice.is_splittable
        form.num_obligations.data = invoice.num_obligations
        
        return render_template('split_invoice.html', form=form, invoice=invoice)

    @app.route('/invoice/<int:id>/split/export')
    @login_required
    def export_split_excel(id):
        invoice = Invoice.query.get_or_404(id)
        if not invoice.is_splittable or invoice.split_status != 'completed':
            flash('La factura no ha sido dividida o no se ha completado el proceso', 'warning')
            return redirect(url_for('invoices_details', id=invoice.id))
        
        handler = InvoiceSplitService(invoice)
        output = handler.generate_excel_report()
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'factura_dividida_{invoice.id}.xlsx'
        )
    
    @app.route('/export/csv')
    @login_required
    def export_csv():
        try:
            si = io.StringIO()
            cw = csv.writer(si)
                    
            cw.writerow(['ID', 'N° Factura', 'Archivo', 'Proveedor', 'Dirección', 'Total', 
                                'Impuestos', 'Fecha', 'Método Pago', 'Productos/Servicios', 'Fecha de Carga'])
                    
            invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
            for invoice in invoices:
                cw.writerow([
                    invoice.id,
                    invoice.invoice_number,
                    invoice.filename,
                    invoice.vendor,
                    invoice.vendor_address,
                    invoice.total,
                    invoice.tax,
                    invoice.date,
                    invoice.payment_method,
                    invoice.items,
                    invoice.created_at.strftime('%Y-%m-%d %H:%M') if invoice.created_at else 'N/A'
                ])
                
            output = io.BytesIO()
            output.write(si.getvalue().encode('utf-8'))
            output.seek(0)
                    
            return send_file(
                output,
                mimetype='text/csv',
                as_attachment=True,
                download_name=f'facturas_{datetime.now().strftime("%Y%m%d_%H%M")}.csv'
                    )
        except Exception as e:
            flash(f'Error al exportar a CSV: {str(e)}', 'danger')
            return redirect(url_for('history'))

    @app.route('/export/excel')
    @login_required
    def export_excel():
        if not EXCEL_ENABLED:
            flash('La exportación a Excel no está disponible en este momento', 'warning')
            return redirect(url_for('history'))
                    
        try:
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output)
            worksheet = workbook.add_worksheet('Facturas')
                    
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#F0F0F0',
                'border': 1
                })
                    
            headers = ['ID', 'N° Factura', 'Archivo', 'Proveedor', 'Dirección', 'Total', 
                            'Impuestos', 'Fecha', 'Método Pago', 'Productos/Servicios', 'Fecha de Carga']
            for col, header in enumerate(headers):
                        worksheet.write(0, col, header, header_format)
                    
            invoices = Invoice.query.order_by(Invoice.created_at.desc()).all()
            for row, invoice in enumerate(invoices, start=1):
                        worksheet.write(row, 0, invoice.id)
                        worksheet.write(row, 1, invoice.invoice_number)
                        worksheet.write(row, 2, invoice.filename)
                        worksheet.write(row, 3, invoice.vendor)
                        worksheet.write(row, 4, invoice.vendor_address)
                        worksheet.write(row, 5, invoice.total)
                        worksheet.write(row, 6, invoice.tax)
                        worksheet.write(row, 7, invoice.date)
                        worksheet.write(row, 8, invoice.payment_method)
                        worksheet.write(row, 9, invoice.items)
                        worksheet.write(row, 10, invoice.created_at.strftime('%Y-%m-%d %H:%M') if invoice.created_at else 'N/A')
                
            for col in range(len(headers)):
                worksheet.set_column(col, col, 20)
                
            workbook.close()
            output.seek(0)
                
            return send_file(
                output,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'facturas_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
                )
            
        except Exception as e:
            flash(f'Error al exportar a Excel: {str(e)}', 'danger')
        return redirect(url_for('history'))

    @app.route('/invoice/<int:id>/details')
    @login_required
    def invoice_details(id):
        invoice = Invoice.query.get_or_404(id)
        
        #Obtener la URL de vista previa si existe el archivo
        preview_url = None
        if invoice.filename:
            preview_url = url_for('uploaded_file', filename=invoice.filename)
        
        return render_template('invoices_details.html', invoice=invoice, preview_url=preview_url)
    
    @app.route('/verify-otp', methods=['GET', 'POST'])
    def verify_otp():
        # Si no hay usuario en proceso de verificación OTP
        if 'otp_user_id' not in session:
            return redirect(url_for('login'))
        
        user = User.query.get(session['otp_user_id'])
        if not user:
            session.pop('otp_user_id', None)
            return redirect(url_for('login'))
        
        form = OTPVerificationForm()
        if form.validate_on_submit():
            if user.verify_totp(form.otp_token.data):
                # Eliminar el ID de usuario de la sesión
                session.pop('otp_user_id', None)
                # Iniciar sesión
                login_user(user)
                next_page = request.args.get('next')
                if not next_page or urlparse(next_page).netloc != '':
                    next_page = url_for('index')
                return redirect(next_page)
            else:
                flash('Código de verificación inválido', 'danger')
        
        return render_template('verify_otp.html', form=form)
    
    @app.route('/profile/security', methods=['GET', 'POST'])
    @login_required
    def security_settings():
        # Para activar 2FA
        enable_form = EnableOTPForm()
        disable_form = DisableOTPForm()
        
        # Generar QR solo si el usuario no tiene 2FA activado
        qr_code = None
        if not current_user.otp_enabled:
            # Generar nuevo secreto si no tiene uno
            if not current_user.otp_secret:
                current_user.generate_otp_secret()
                db.session.commit()
            
            # Generar imagen QR
            import qrcode
            import io
            import base64
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(current_user.get_totp_uri())
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffered = io.BytesIO()
            img.save(buffered)
            qr_code = base64.b64encode(buffered.getvalue()).decode()
        
        # Procesar activación de 2FA
        if enable_form.validate_on_submit() and not current_user.otp_enabled:
            if current_user.verify_totp(enable_form.otp_token.data):
                current_user.otp_enabled = True
                db.session.commit()
                flash('Autenticación de dos factores activada correctamente', 'success')
                return redirect(url_for('security_settings'))
            else:
                flash('Código de verificación inválido', 'danger')
        
        # Procesar desactivación de 2FA
        if disable_form.validate_on_submit() and current_user.otp_enabled:
            if current_user.verify_totp(disable_form.otp_token.data):
                current_user.otp_enabled = False
                db.session.commit()
                flash('Autenticación de dos factores desactivada correctamente', 'success')
                return redirect(url_for('security_settings'))
            else:
                flash('Código de verificación inválido', 'danger')
        
        return render_template('security_settings.html', 
                              enable_form=enable_form, 
                              disable_form=disable_form, 
                              qr_code=qr_code)

    @app.route('/history', methods=['GET'])
    @login_required
    def history():
        form = SearchForm(request.args)
        query = Invoice.query

        try:
            if form.search_query.data:
                search = f"%{form.search_query.data}%"
                query = query.filter(or_(
                    Invoice.vendor.ilike(search),
                    Invoice.filename.ilike(search)
                ))

            if form.date_from.data:
                try:
                    date_from = datetime.strptime(str(form.date_from.data), '%Y-%m-%d')
                    query = query.filter(func.date(Invoice.date) >= date_from.date())
                except (ValueError, TypeError):
                    flash('Formato de fecha "desde" inválido', 'warning')

            if form.date_to.data:
                try:
                    date_to = datetime.strptime(str(form.date_to.data), '%Y-%m-%d')
                    query = query.filter(func.date(Invoice.date) <= date_to.date())
                except (ValueError, TypeError):
                    flash('Formato de fecha "hasta" inválido', 'warning')

            if form.amount_min.data is not None and str(form.amount_min.data).strip():
                try:
                    min_amount = float(form.amount_min.data)
                    query = query.filter(cast(func.replace(func.replace(Invoice.total, ',', ''), '$', ''), Float) >= min_amount)
                except (ValueError, TypeError):
                    flash('Formato de monto mínimo inválido', 'warning')

            if form.amount_max.data is not None and str(form.amount_max.data).strip():
                try:
                    max_amount = float(form.amount_max.data)
                    query = query.filter(cast(func.replace(func.replace(Invoice.total, ',', ''), '$', ''), Float) <= max_amount)
                except (ValueError, TypeError):
                    flash('Formato de monto máximo inválido', 'warning')

            invoices = query.order_by(Invoice.created_at.desc()).all()
                
        except Exception as e:
            flash(f'Error en la búsqueda: {str(e)}', 'danger')
            invoices = []

        return render_template('history.html', invoices=invoices, form=form)
##########################################################################################
    @app.route('/edit_invoice/<int:id>', methods=['GET', 'POST'])
    @login_required
    def edit_invoice(id):
        invoice = Invoice.query.get_or_404(id)
        form = EditInvoiceForm()

        if request.method == 'GET':
            form.vendor.data = invoice.vendor
            form.total.data = invoice.total
            form.date.data = invoice.date
            form.invoice_number.data = invoice.invoice_number
            form.vendor_address.data = invoice.vendor_address
            form.items.data = invoice.items
            form.tax.data = invoice.tax
            form.payment_method.data = invoice.payment_method

        if form.validate_on_submit():
            try:
                invoice.vendor = form.vendor.data
                invoice.total = form.total.data
                invoice.date = form.date.data
                invoice.invoice_number = form.invoice_number.data
                invoice.vendor_address = form.vendor_address.data
                invoice.items = form.items.data
                invoice.tax = form.tax.data
                invoice.payment_method = form.payment_method.data
                    
                db.session.commit()
                flash('Documento actualizado exitosamente!', 'success')
                return redirect(url_for('history'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al actualizar el documento: {str(e)}', 'danger')

        preview_url = url_for('uploaded_file', filename=invoice.filename) if invoice.filename else None
        return render_template('edit_invoice.html', form=form, invoice=invoice, preview_url=preview_url)
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user is None or not user.check_password(form.password.data):
                flash('Usuario o contraseña inválidos', 'danger')
                return redirect(url_for('login'))
            
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)
        return render_template('login.html', title='Iniciar Sesión', form=form)
    
    
    
    @app.route('/admin/users', methods=['GET', 'POST'])
    
    @login_required
    @admin_required
    def admin_users():
        form = UserCreateForm()
        if form.validate_on_submit():
            try:
                user = User(
                    username=form.username.data,
                    email=form.email.data,
                    role=form.role.data,
                    estudio=form.estudio.data  # Agregar el nuevo campo
                )
                user.set_password(form.password.data)
                db.session.add(user)
                db.session.commit()
                flash('Usuario creado exitosamente', 'success')
                return redirect(url_for('admin_users'))
            except Exception as e:
                db.session.rollback()
                flash(f'Error al crear usuario: {str(e)}', 'danger')

        users = User.query.order_by(User.created_at.desc()).all()
        return render_template('admin/users.html', form=form, users=users)

    @app.route('/logout')
    def logout():
        logout_user()
        return redirect(url_for('index'))
    
    return app

def init_app():
    app = create_app()
    with app.app_context():
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'])
        if not os.path.exists('invoices.db'):
            db.create_all()
    return app

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            flash('No tiene permisos para acceder a esta página.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

if __name__ == '__main__':
    app = init_app()
    app.run(debug=True)