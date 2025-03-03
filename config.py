import os
from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient

class Config:
    SECRET_KEY = '581cec714d8043ad88f46a2823601f9b'  # Cambia esto por una clave segura
    SQLALCHEMY_DATABASE_URI = 'sqlite:///invoices.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
    AZURE_ENDPOINT = "https://gpsdocuia.cognitiveservices.azure.com/"
    AZURE_KEY = "3ec19ea8ba564166a8db87ff97eb0fe1"
    
    # Configuraciones de Celery
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
