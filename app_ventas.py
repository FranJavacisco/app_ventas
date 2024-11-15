import sys
import psycopg2
from datetime import datetime, timedelta
from decimal import Decimal
import pandas as pd
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                           QComboBox, QMessageBox, QGridLayout, QDateEdit)
from PyQt6.QtCore import Qt, QDate
from PyQt6.QtGui import QFont, QDoubleValidator

class DatabaseConnection:
    def __init__(self):
        # Configura con las credenciales de postgres.new
        self.config = {
            'dbname': 'tu_base_de_datos',
            'user': 'tu_usuario',
            'password': 'tu_contraseña',
            'host': 'ep-xxx-xxx.region.aws.neon.tech',
            'port': '5432',
            'sslmode': 'require'
        }
    
    def connect(self):
        return psycopg2.connect(**self.config)

class VentasApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Control de Ventas Diarias")
        self.setMinimumSize(800, 600)
        
        self.db = DatabaseConnection()
        self.init_database()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        self.create_form(layout)
        self.create_reports_section(layout)
        
    def init_database(self):
        conn = self.db.connect()
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ventas (
                id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
                fecha DATE NOT NULL,
                precio_ripley NUMERIC(10,2),
                precio_otro NUMERIC(10,2),
                seguro NUMERIC(10,2),
                garantia NUMERIC(10,2),
                captacion_express NUMERIC(10,2),
                captacion_debito NUMERIC(10,2),
                despacho NUMERIC(10,2),
                tipo_producto TEXT
            )
        ''')
        conn.commit()
        cursor.close()
        conn.close()
        
    def create_form(self, layout):
        form_layout = QGridLayout()
        
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        
        self.fields = {
            'precio_ripley': QLineEdit(),
            'precio_otro': QLineEdit(),
            'seguro': QLineEdit(),
            'garantia': QLineEdit(),
            'captacion_express': QLineEdit(),
            'captacion_debito': QLineEdit(),
            'despacho': QLineEdit()
        }
        
        self.tipo_producto = QComboBox()
        self.tipo_producto.addItems(['Electrónica', 'Línea Blanca', 'Muebles', 'Ropa', 'Otros'])
        
        for field in self.fields.values():
            validator = QDoubleValidator()
            validator.setDecimals(2)
            field.setValidator(validator)
            field.textChanged.connect(self.format_number)
        
        labels = ['Fecha:', 'Precio Ripley:', 'Precio Otro Medio:', 'Seguro:', 
                 'Garantía:', 'Captación Express:', 'Captación Débito:', 
                 'Despacho:', 'Tipo de Producto:']
        
        widgets = [self.date_edit] + list(self.fields.values()) + [self.tipo_producto]
        
        for i, (label, widget) in enumerate(zip(labels, widgets)):
            form_layout.addWidget(QLabel(label), i, 0)
            form_layout.addWidget(widget, i, 1)
        
        save_button = QPushButton("Guardar Venta")
        save_button.clicked.connect(self.save_sale)
        form_layout.addWidget(save_button, len(labels), 0, 1, 2)
        
        layout.addLayout(form_layout)
        
    def create_reports_section(self, layout):
        reports_layout = QHBoxLayout()
        
        self.report_type = QComboBox()
        self.report_type.addItems(['Diario', 'Semanal', 'Mensual'])
        
        generate_button = QPushButton("Generar Reporte")
        generate_button.clicked.connect(self.generate_report)
        
        reports_layout.addWidget(QLabel("Tipo de Reporte:"))
        reports_layout.addWidget(self.report_type)
        reports_layout.addWidget(generate_button)
        
        layout.addLayout(reports_layout)
        
    def format_number(self, text):
        if not text:
            return
            
        sender = self.sender()
        text = text.replace('.', '').replace(',', '')
        
        try:
            number = int(text)
            formatted = "{:,}".format(number)
            sender.blockSignals(True)
            sender.setText(formatted)
            sender.blockSignals(False)
        except ValueError:
            pass
            
    def save_sale(self):
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            values = {
                field: Decimal(value.text().replace(',', '')) 
                for field, value in self.fields.items()
            }
            
            cursor.execute('''
                INSERT INTO ventas (
                    fecha, precio_ripley, precio_otro, seguro, garantia,
                    captacion_express, captacion_debito, despacho, tipo_producto
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''', (
                self.date_edit.date().toPyDate(),
                values['precio_ripley'],
                values['precio_otro'],
                values['seguro'],
                values['garantia'],
                values['captacion_express'],
                values['captacion_debito'],
                values['despacho'],
                self.tipo_producto.currentText()
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            QMessageBox.information(self, "Éxito", "Venta registrada correctamente")
            
            for field in self.fields.values():
                field.clear()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error al guardar la venta: {str(e)}")
            
    def generate_report(self):
        try:
            conn = self.db.connect()
            
            report_type = self.report_type.currentText()
            current_date = datetime.now()
            
            if report_type == 'Diario':
                start_date = current_date.date()
                end_date = start_date
            elif report_type == 'Semanal':
                start_date = (current_date - timedelta(days=current_date.weekday())).date()
                end_date = (start_date + timedelta(days=6))
            else:  # Mensual
                start_date = current_date.replace(day=1).date()
                if current_date.month == 12:
                    end_date = current_date.replace(year=current_date.year + 1, 
                                                 month=1, day=1).date()
                else:
                    end_date = current_date.replace(month=current_date.month + 1, 
                                                 day=1).date()
                end_date = end_date - timedelta(days=1)
            
            query = '''
                SELECT fecha, 
                       CASE 
                           WHEN precio_ripley > 0 THEN ROUND(precio_ripley / 1.19, 2)
                           ELSE precio_ripley 
                       END as precio_ripley_sin_iva,
                       CASE 
                           WHEN precio_otro > 0 THEN ROUND(precio_otro / 1.19, 2)
                           ELSE precio_otro 
                       END as precio_otro_sin_iva,
                       CASE 
                           WHEN seguro > 0 THEN ROUND(seguro / 1.19, 2)
                           ELSE seguro 
                       END as seguro_sin_iva,
                       CASE 
                           WHEN garantia > 0 THEN ROUND(garantia / 1.19, 2)
                           ELSE garantia 
                       END as garantia_sin_iva,
                       captacion_express,
                       captacion_debito,
                       CASE 
                           WHEN despacho > 0 THEN ROUND(despacho / 1.19, 2)
                           ELSE despacho 
                       END as despacho_sin_iva,
                       tipo_producto
                FROM ventas
                WHERE fecha BETWEEN %s AND %s
            '''
            
            df = pd.read_sql_query(query, conn, params=[start_date, end_date])
            conn.close()
            
            filename = f"reporte_{report_type.lower()}_{start_date}.xlsx"
            df.to_excel(filename, index=False)
            
            QMessageBox.information(self, "Éxito", 
                                  f"Reporte generado correctamente: {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                               f"Error al generar el reporte: {str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VentasApp()
    window.show()
    sys.exit(app.exec())