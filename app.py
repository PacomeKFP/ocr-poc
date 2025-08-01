from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
from werkzeug.utils import secure_filename
from ocr.id_card_data_extractor import IDCardDataExtractor
from ocr.card_side import CardSide
from ocr.card_version import CardVersion
import logging
import sys

# Configuration du logging pour Flask
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # Disable caching
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutes timeout

# Créer le dossier uploads s'il n'existe pas
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Extensions autorisées
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

# Configuration des modèles (correction du chemin)
BASE_MODEL_PATH = "./models/finetunes/qwen3-0.6b-lora-cni-2018-front"  # Chemin corrigé
LORA_ADAPTER_PATH = "./models/finetunes/qwen3-0.6b-cni-lora/checkpoint-938"

# Choix du modèle : "base" ou "lora"
USE_LORA = False  # Mettre False pour utiliser le modèle de base

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Variable globale pour l'extracteur
extractor = None

def init_extractor():
    """Initialise l'extracteur une seule fois"""
    global extractor
    if extractor is None:
        if USE_LORA:
            logger.info("Initializing IDCardDataExtractor with LoRA adapter at startup...")
            extractor = IDCardDataExtractor(BASE_MODEL_PATH, lora_adapter_path=LORA_ADAPTER_PATH)
            logger.info("IDCardDataExtractor with LoRA initialized successfully at startup")
        else:
            logger.info("Initializing IDCardDataExtractor with base model at startup...")
            extractor = IDCardDataExtractor(BASE_MODEL_PATH)
            logger.info("IDCardDataExtractor with base model initialized successfully at startup")
    return extractor



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/test', methods=['GET'])
def test_extractor():
    """Route de test pour vérifier l'état de l'extracteur"""
    logger.info("=== TEST EXTRACTEUR ===")
    try:
        current_extractor = init_extractor()
        model_info = {}
        if hasattr(current_extractor.llm_post_processor, 'get_model_info'):
            model_info = current_extractor.llm_post_processor.get_model_info()
        
        return jsonify({
            'status': 'OK',
            'extractor_loaded': current_extractor is not None,
            'model_info': model_info
        })
    except Exception as e:
        logger.error(f"Erreur test extracteur: {e}", exc_info=True)
        return jsonify({'status': 'ERROR', 'error': str(e)}), 500

@app.route('/upload', methods=['POST'])
def upload_file():
    logger.info("=== DÉBUT UPLOAD REQUEST ===")
    
    if 'file' not in request.files:
        logger.warning("Aucun fichier dans la requête")
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    file = request.files['file']
    version = request.form.get('version')
    side = request.form.get('side')
    
    logger.info(f"Fichier reçu: {file.filename}, Version: {version}, Side: {side}")
    
    if file.filename == '':
        logger.warning("Nom de fichier vide")
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    if not version or not side:
        logger.warning(f"Paramètres manquants - Version: {version}, Side: {side}")
        return jsonify({'error': 'Version et face requises'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Sauvegarder le fichier
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            logger.info(f"Sauvegarde du fichier: {file_path}")
            file.save(file_path)
            
            # Initialiser l'extracteur si nécessaire
            logger.info("Vérification de l'extracteur...")
            current_extractor = init_extractor()
            logger.info("Extracteur prêt")
            
            # Convertir les paramètres
            card_version = CardVersion.v2018 if version == '2018' else CardVersion.v2025
            card_side = CardSide.RECTO if side == 'recto' else CardSide.VERSO
            logger.info(f"Paramètres convertis - Version: {card_version}, Side: {card_side}")
            
            # Extraire les données
            logger.info(f"Début extraction pour {file_path}")
            raw_text, extracted_data = current_extractor.extract(file_path, card_version, card_side)
            logger.info("Extraction terminée avec succès")
            
            # Nettoyer le fichier temporaire
            logger.info("Nettoyage du fichier temporaire")
            os.remove(file_path)
            
            logger.info("=== UPLOAD RÉUSSI ===")
            return jsonify({
                'success': True,
                'raw_text': raw_text,
                'extracted_data': extracted_data
            })
            
        except Exception as e:
            logger.error(f"ERREUR lors du traitement: {str(e)}", exc_info=True)
            # Nettoyer le fichier en cas d'erreur
            if 'file_path' in locals() and os.path.exists(file_path):
                logger.info("Nettoyage du fichier en cas d'erreur")
                os.remove(file_path)
            return jsonify({'error': f'Erreur lors du traitement: {str(e)}'}), 500
    
    logger.warning(f"Format de fichier non autorisé: {file.filename}")
    return jsonify({'error': 'Format de fichier non autorisé'}), 400

if __name__ == '__main__':
    logger.info("Démarrage de l'application Flask...")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)