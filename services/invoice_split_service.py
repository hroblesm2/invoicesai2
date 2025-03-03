from decimal import Decimal
import xlsxwriter
from io import BytesIO
from models import InvoiceSplit, db

class InvoiceSplitHandler:
    def __init__(self, invoice):
        self.invoice = invoice
        
    def calculate_split_amount(self):
        """Calcula el monto dividido por obligación"""
        if not self.invoice.total:
            return 0
            
        # Limpia el string de total y convierte a decimal
        total_str = self.invoice.total.replace('$', '').replace(',', '')
        try:
            total = Decimal(total_str)
            return float(total / self.invoice.num_obligations)
        except:
            return 0
            
    def create_splits(self):
        """Crea los registros de división"""
        if not self.invoice.is_splittable or self.invoice.split_status == 'completed':
            return False
            
        # Elimina divisiones anteriores si existen
        InvoiceSplit.query.filter_by(invoice_id=self.invoice.id).delete()
        
        split_amount = self.calculate_split_amount()
        
        for i in range(self.invoice.num_obligations):
            split = InvoiceSplit(
                invoice_id=self.invoice.id,
                obligation_number=i + 1,
                amount=split_amount,
                description=f'Obligación {i + 1} de {self.invoice.num_obligations}'
            )
            db.session.add(split)
        
        self.invoice.split_status = 'completed'
        db.session.commit()
        return True
        
    def generate_excel_report(self):
        """Genera reporte Excel con la división de la factura"""
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet('División de Factura')
        
        # Formatos
        header_format = workbook.add_format({
            'bold': True,
            'align': 'center',
            'bg_color': '#F0F0F0',
            'border': 1
        })
        
        money_format = workbook.add_format({
            'num_format': '$#,##0.00',
            'align': 'right'
        })
        
        # Encabezados
        headers = [
            'N° Factura',
            'Proveedor',
            'N° Obligación',
            'Monto Original',
            'Monto Dividido',
            'Fecha',
            'Descripción'
        ]
        
        for col, header in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            worksheet.set_column(col, col, 15)
        
        # Datos
        row = 1
        splits = InvoiceSplit.query.filter_by(invoice_id=self.invoice.id).all()
        
        for split in splits:
            worksheet.write(row, 0, self.invoice.invoice_number)
            worksheet.write(row, 1, self.invoice.vendor)
            worksheet.write(row, 2, split.obligation_number)
            worksheet.write(row, 3, float(self.invoice.total.replace('$', '').replace(',', '')), money_format)
            worksheet.write(row, 4, split.amount, money_format)
            worksheet.write(row, 5, self.invoice.date)
            worksheet.write(row, 6, split.description)
            row += 1
            
        workbook.close()
        output.seek(0)
        return output 
    
    