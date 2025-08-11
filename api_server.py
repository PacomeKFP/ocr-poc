#!/usr/bin/env python3
"""
API REST Flask pour le service OCR
Sert d'interface entre l'application web et le serveur gRPC
"""

import os
import grpc
import json
import logging
import traceback
import time
from datetime import datetime
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
import ocr_service_pb2
import ocr_service_pb2_grpc
import uuid
from functools import wraps

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}
GRPC_SERVER_HOST = 'localhost:50051'

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
metrics_handler = logging.FileHandler('api_metrics.log')
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

def call_grpc_service(request_id, image_data, version, side, thinking_mode=False, retry_count=0):
    """Appelle le service gRPC pour traiter l'image avec retry automatique"""
    max_retries = 3
    retry_delay = [5, 10, 20]  # Délais progressifs
    
    logger.info(f"[{request_id}] Tentative {retry_count + 1}/{max_retries + 1} - Connexion au serveur gRPC {GRPC_SERVER_HOST}")
    logger.info(f"[{request_id}] Paramètres: version={version}, side={side}, thinking_mode={thinking_mode}, taille_image={len(image_data)} bytes")
    
    try:
        # Test de connexion d'abord
        logger.info(f"[{request_id}] Test de connexion au serveur gRPC...")
        with grpc.insecure_channel(GRPC_SERVER_HOST) as channel:
            try:
                grpc.channel_ready_future(channel).result(timeout=10)
                logger.info(f"[{request_id}] Connexion gRPC établie avec succès")
            except grpc.FutureTimeoutError:
                raise Exception("Timeout lors de la connexion au serveur gRPC")
            
            stub = ocr_service_pb2_grpc.OCRServiceStub(channel)
            
            # Créer la requête
            logger.info(f"[{request_id}] Création de la requête gRPC...")
            grpc_request = ocr_service_pb2.OCRRequest(
                image_data=image_data,
                version=version,
                side=side,
                thinking_mode=thinking_mode
            )
            
            # Appeler le service avec timeout étendu
            logger.info(f"[{request_id}] Envoi de la requête au serveur gRPC (timeout: 300s)...")
            start_grpc = time.time()
            
            response = stub.ExtractData(grpc_request, timeout=300)
            
            grpc_time = time.time() - start_grpc
            logger.info(f"[{request_id}] Réponse reçue du serveur gRPC en {grpc_time:.2f}s")
            logger.info(f"[{request_id}] Statut de la réponse: success={response.success}")
            
            if response.success:
                logger.info(f"[{request_id}] Extraction réussie - Taille texte brut: {len(response.raw_text)} chars")
                logger.info(f"[{request_id}] Taille données extraites: {len(response.extracted_data)} chars")
            else:
                logger.warning(f"[{request_id}] Extraction échouée - Erreur: {response.error}")
            
            return {
                'success': response.success,
                'raw_text': response.raw_text,
                'extracted_data': json.loads(response.extracted_data) if response.extracted_data else {},
                'error': response.error,
                'processing_time': grpc_time,
                'retry_count': retry_count
            }
            
    except grpc.RpcError as e:
        error_msg = f"Erreur gRPC: {e.code()} - {e.details()}"
        logger.error(f"[{request_id}] {error_msg}")
        
        # Retry automatique pour certaines erreurs
        if retry_count < max_retries and e.code() in [grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED]:
            delay = retry_delay[min(retry_count, len(retry_delay) - 1)]
            logger.info(f"[{request_id}] Retry dans {delay}s (tentative {retry_count + 1}/{max_retries})...")
            time.sleep(delay)
            return call_grpc_service(request_id, image_data, version, side, thinking_mode, retry_count + 1)
        
        return {
            'success': False,
            'raw_text': '',
            'extracted_data': {},
            'error': error_msg,
            'retry_count': retry_count,
            'final_failure': True
        }
        
    except Exception as e:
        error_msg = f"Erreur lors de l'appel gRPC: {str(e)}"
        logger.error(f"[{request_id}] {error_msg}")
        logger.error(f"[{request_id}] Traceback: {traceback.format_exc()}")
        
        # Retry pour les erreurs de connexion
        if retry_count < max_retries and ("connection" in str(e).lower() or "timeout" in str(e).lower()):
            delay = retry_delay[min(retry_count, len(retry_delay) - 1)]
            logger.info(f"[{request_id}] Retry dans {delay}s (tentative {retry_count + 1}/{max_retries})...")
            time.sleep(delay)
            return call_grpc_service(request_id, image_data, version, side, thinking_mode, retry_count + 1)
        
        return {
            'success': False,
            'raw_text': '',
            'extracted_data': {},
            'error': error_msg,
            'retry_count': retry_count,
            'final_failure': True
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
        thinking_mode = request.form.get('thinking_mode', 'false').lower() == 'true'
        
        logger.info(f"[{request_id}] Paramètres: version={version}, side={side}, thinking_mode={thinking_mode}")
        
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
        
        # Appeler le service gRPC avec gestion d'erreurs
        logger.info(f"[{request_id}] Appel du service gRPC...")
        result = call_grpc_service(request_id, image_data, version, side, thinking_mode)
        
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
            # Gestion des erreurs avec codes spécifiques
            error_code = 'PROCESSING_ERROR'
            if 'final_failure' in result:
                error_code = 'SERVICE_UNAVAILABLE' if result['retry_count'] >= 2 else 'TEMPORARY_ERROR'
            
            logger.error(f"[{request_id}] Extraction échouée: {result['error']}")
            
            response_data = {
                'success': False,
                'error': result['error'],
                'error_code': error_code,
                'meta': {
                    'retry_count': result.get('retry_count', 0),
                    'can_retry': result.get('retry_count', 0) < 3,
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            # Status code selon le type d'erreur
            status_code = 503 if error_code == 'SERVICE_UNAVAILABLE' else 500
            return jsonify(response_data), status_code
            
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
        
        # Test de connexion au serveur gRPC
        grpc_status = 'unknown'
        grpc_error = None
        
        try:
            with grpc.insecure_channel(GRPC_SERVER_HOST) as channel:
                grpc.channel_ready_future(channel).result(timeout=5)
                grpc_status = 'connected'
        except Exception as e:
            grpc_status = 'disconnected'
            grpc_error = str(e)
            
        health_time = time.time() - health_start
        
        # Calculer les métriques
        success_rate = (success_counter / request_counter * 100) if request_counter > 0 else 0
        avg_processing_time = (total_processing_time / success_counter) if success_counter > 0 else 0
        
        health_data = {
            'status': 'healthy' if grpc_status == 'connected' else 'degraded',
            'timestamp': datetime.now().isoformat(),
            'services': {
                'api': {
                    'status': 'running',
                    'uptime': time.time() - app.start_time if hasattr(app, 'start_time') else 'unknown'
                },
                'grpc_server': {
                    'status': grpc_status,
                    'host': GRPC_SERVER_HOST,
                    'error': grpc_error
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
        
        status_code = 200 if grpc_status == 'connected' else 503
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

if __name__ == '__main__':
    print(" Démarrage de l'API REST OCR...")
    print(f" Interface web disponible sur: http://localhost:5000")
    print(f" Serveur gRPC attendu sur: {GRPC_SERVER_HOST}")
    print(f" Logs API: api_server.log")
    print(f" Métriques: api_metrics.log")
    
    # Enregistrer le temps de démarrage pour les métriques uptime
    app.start_time = time.time()
    
    logger.info("API Server démarré avec logging détaillé et recovery automatique")
    
    app.run(host='0.0.0.0', port=5000, debug=False)  # Debug False en production