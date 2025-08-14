#!/usr/bin/env python3
"""
API REST Flask pour le service OCR
Interface directe avec le coeur OCR
"""

import os
import tempfile
import json
import logging
import traceback
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import uuid
from functools import wraps

# Import du coeur OCR
from ocr.id_card_data_extractor import IDCardDataExtractor
from ocr.card_side import CardSide
from ocr.card_version import CardVersion

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}

# Setup logging détaillé
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler('api_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Logger spécifique pour les métriques
metrics_logger = logging.getLogger('metrics')
metrics_handler = logging.FileHandler('api_metrics.log', encoding='utf-8')
metrics_handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
metrics_logger.addHandler(metrics_handler)
metrics_logger.setLevel(logging.INFO)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Créer les dossiers nécessaires
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs('logs', exist_ok=True)

# Compteurs globaux pour monitoring
request_counter = 0
success_counter = 0
error_counter = 0
total_processing_time = 0

def log_metrics(func):
    """Décorateur pour logger les métriques de performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        global request_counter, success_counter, error_counter, total_processing_time
        
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        request_counter += 1
        
        logger.info(f"[{request_id}] Nouvelle requête {func.__name__} - Total requêtes: {request_counter}")
        
        try:
            result = func(request_id, *args, **kwargs)
            processing_time = time.time() - start_time
            total_processing_time += processing_time
            success_counter += 1
            
            logger.info(f"[{request_id}] Succès en {processing_time:.2f}s - Succès total: {success_counter}")
            metrics_logger.info(f"SUCCESS,{request_id},{processing_time:.2f},{request_counter},{success_counter},{error_counter}")
            
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_counter += 1
            
            logger.error(f"[{request_id}] Erreur après {processing_time:.2f}s - Erreurs total: {error_counter}")
            logger.error(f"[{request_id}] Détails erreur: {str(e)}")
            logger.error(f"[{request_id}] Traceback: {traceback.format_exc()}")
            metrics_logger.info(f"ERROR,{request_id},{processing_time:.2f},{request_counter},{success_counter},{error_counter}")
            
            raise
    
    return wrapper

def allowed_file(filename):
    """Vérifie si l'extension de fichier est autorisée"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Instance globale de l'extracteur OCR
ocr_extractor = None

def init_ocr_extractor():
    """Initialise l'extracteur OCR une seule fois"""
    global ocr_extractor
    if ocr_extractor is None:
        logger.info("Initialisation de l'extracteur OCR...")
        ocr_extractor = IDCardDataExtractor()
        logger.info("Extracteur OCR initialisé avec succès")

def process_ocr_request(request_id, image_data, version, side):
    """Traite une requête OCR avec l'extracteur local"""
    logger.info(f"[{request_id}] Traitement OCR direct")
    logger.info(f"[{request_id}] Paramètres: version={version}, side={side}, taille_image={len(image_data)} bytes")
    
    try:
        # S'assurer que l'extracteur est initialisé
        if ocr_extractor is None:
            init_ocr_extractor()
        
        # Sauvegarder l'image temporairement
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
            temp_file.write(image_data)
            temp_path = temp_file.name
        
        try:
            # Convertir les paramètres
            card_version = CardVersion.v2018 if version == '2018' else CardVersion.v2025
            card_side = CardSide.RECTO if side == 'recto' else CardSide.VERSO
            
            logger.info(f"[{request_id}] Début extraction OCR...")
            start_time = time.time()
            
            # Extraire les données
            raw_text, extracted_data = ocr_extractor.extract(
                temp_path, 
                card_version, 
                card_side
            )
            
            processing_time = time.time() - start_time
            logger.info(f"[{request_id}] Extraction réussie en {processing_time:.2f}s")
            logger.info(f"[{request_id}] Taille texte brut: {len(raw_text)} chars")
            
            return {
                'success': True,
                'raw_text': raw_text,
                'extracted_data': extracted_data if extracted_data else {},
                'error': '',
                'processing_time': processing_time
            }
            
        finally:
            # Nettoyer le fichier temporaire
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                
    except Exception as e:
        error_msg = f"Erreur lors du traitement OCR: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}")
        logger.error(f"[{request_id}] Traceback: {traceback.format_exc()}")
        
        return {
            'success': False,
            'raw_text': '',
            'extracted_data': {},
            'error': error_msg,
            'processing_time': 0
        }

@app.route('/')
def index():
    """Page d'accueil avec formulaire d'upload"""
    return render_template('index.html')

@app.route('/api/extract', methods=['POST'])
@log_metrics
def extract_data(request_id):
    """API endpoint pour l'extraction de données OCR avec gestion d'erreurs robuste"""
    try:
        logger.info(f"[{request_id}] Début de l'extraction OCR")
        
        # Vérifications détaillées des paramètres
        if 'image' not in request.files:
            logger.warning(f"[{request_id}] Aucun fichier fourni")
            return jsonify({
                'success': False,
                'error': 'Aucun fichier fourni',
                'error_code': 'NO_FILE'
            }), 400
        
        file = request.files['image']
        if file.filename == '':
            logger.warning(f"[{request_id}] Aucun fichier sélectionné")
            return jsonify({
                'success': False,
                'error': 'Aucun fichier sélectionné',
                'error_code': 'EMPTY_FILENAME'
            }), 400
        
        logger.info(f"[{request_id}] Fichier reçu: {file.filename}")
        
        # Vérifier l'extension
        if not allowed_file(file.filename):
            logger.warning(f"[{request_id}] Type de fichier non autorisé: {file.filename}")
            return jsonify({
                'success': False,
                'error': f'Type de fichier non autorisé: {file.filename}',
                'error_code': 'INVALID_FILE_TYPE',
                'allowed_types': list(ALLOWED_EXTENSIONS)
            }), 400
        
        # Récupérer et valider les paramètres
        version = request.form.get('version', '2018')
        side = request.form.get('side', 'recto')
        
        logger.info(f"[{request_id}] Paramètres: version={version}, side={side}")
        
        if version not in ['2018', '2025']:
            logger.warning(f"[{request_id}] Version invalide: {version}")
            return jsonify({
                'success': False,
                'error': f'Version invalide: {version}',
                'error_code': 'INVALID_VERSION',
                'valid_versions': ['2018', '2025']
            }), 400
        
        if side not in ['recto', 'verso']:
            logger.warning(f"[{request_id}] Côté invalide: {side}")
            return jsonify({
                'success': False,
                'error': f'Côté invalide: {side}',
                'error_code': 'INVALID_SIDE',
                'valid_sides': ['recto', 'verso']
            }), 400
        
        # Lire les données du fichier
        logger.info(f"[{request_id}] Lecture du fichier...")
        image_data = file.read()
        
        if len(image_data) == 0:
            logger.warning(f"[{request_id}] Fichier vide")
            return jsonify({
                'success': False,
                'error': 'Fichier image vide',
                'error_code': 'EMPTY_FILE'
            }), 400
        
        logger.info(f"[{request_id}] Fichier lu avec succès: {len(image_data)} bytes")
        
        # Traiter avec le coeur OCR
        logger.info(f"[{request_id}] Traitement OCR direct...")
        result = process_ocr_request(request_id, image_data, version, side)
        
        # Analyse du résultat
        if result['success']:
            logger.info(f"[{request_id}] Extraction réussie")
            response_data = {
                'success': True,
                'raw_text': result['raw_text'],
                'extracted_data': result['extracted_data'],
                'meta': {
                    'processing_time': result.get('processing_time', 0),
                    'retry_count': result.get('retry_count', 0),
                    'timestamp': datetime.now().isoformat()
                }
            }
            return jsonify(response_data)
        else:
            # Gestion des erreurs
            logger.error(f"[{request_id}] Extraction échouée: {result['error']}")
            
            response_data = {
                'success': False,
                'error': result['error'],
                'error_code': 'PROCESSING_ERROR',
                'meta': {
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            return jsonify(response_data), 500
            
    except Exception as e:
        logger.error(f"[{request_id}] Erreur critique dans extract_data: {str(e)}")
        logger.error(f"[{request_id}] Traceback: {traceback.format_exc()}")
        
        return jsonify({
            'success': False,
            'error': 'Erreur interne du serveur',
            'error_code': 'INTERNAL_ERROR',
            'debug_info': str(e) if app.debug else None,
            'meta': {
                'timestamp': datetime.now().isoformat()
            }
        }), 500

@app.route('/api/health')
def health_check():
    """Endpoint de santé détaillé avec métriques"""
    try:
        health_start = time.time()
        
        # Test d'initialisation de l'extracteur OCR
        ocr_status = 'unknown'
        ocr_error = None
        
        try:
            if ocr_extractor is None:
                init_ocr_extractor()
            ocr_status = 'ready'
        except Exception as e:
            ocr_status = 'error'
            ocr_error = str(e)
            
        health_time = time.time() - health_start
        
        # Calculer les métriques
        success_rate = (success_counter / request_counter * 100) if request_counter > 0 else 0
        avg_processing_time = (total_processing_time / success_counter) if success_counter > 0 else 0
        
        health_data = {
            'status': 'healthy' if ocr_status == 'ready' else 'degraded',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'api': {
                    'status': 'running',
                    'uptime': time.time() - app.start_time if hasattr(app, 'start_time') else 'unknown'
                },
                'ocr_extractor': {
                    'status': ocr_status,
                    'error': ocr_error
                }
            },
            'metrics': {
                'total_requests': request_counter,
                'successful_requests': success_counter,
                'failed_requests': error_counter,
                'success_rate_percent': round(success_rate, 2),
                'average_processing_time_seconds': round(avg_processing_time, 2)
            },
            'system': {
                'disk_space_mb': get_disk_space(),
                'log_file_size_mb': get_log_file_size()
            }
        }
        
        status_code = 200 if ocr_status == 'ready' else 503
        return jsonify(health_data), status_code
        
    except Exception as e:
        logger.error(f"Erreur dans health_check: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 503

def get_disk_space():
    """Obtient l'espace disque disponible en MB"""
    try:
        import shutil
        total, used, free = shutil.disk_usage(".")
        return round(free / (1024*1024), 2)
    except:
        return 'unknown'

def get_log_file_size():
    """Obtient la taille des fichiers de log en MB"""
    try:
        size = 0
        for log_file in ['api_server.log', 'api_metrics.log']:
            if os.path.exists(log_file):
                size += os.path.getsize(log_file)
        return round(size / (1024*1024), 2)
    except:
        return 'unknown'

# Initialisation au niveau module (pour Gunicorn)
# Initialiser l'extracteur OCR au démarrage
init_ocr_extractor()

# Enregistrer le temps de démarrage pour les métriques uptime
app.start_time = time.time()

logger.info("API Server configuré pour Gunicorn")

if __name__ == '__main__':
    # Mode développement - Flask dev server
    print(" Démarrage de l'API REST OCR (mode développement)...")
    print(f" Interface web disponible sur: http://localhost:8080")
    print(f" Logs API: api_server.log")
    print(f" Métriques: api_metrics.log")
    
    app.run(host='0.0.0.0', port=8080, debug=True)