# Service OCR gRPC - Guide Utilisateur

## 📋 Description

Service OCR simple et efficace pour l'extraction de données des cartes d'identité camerounaises (versions 2018 et 2025) utilisant gRPC et des modèles Qwen fine-tunés.

## 🚀 Démarrage Rapide

### 1. Génération des fichiers gRPC

```bash
python generate_grpc.py
```

### 2. Démarrage avec Docker (Recommandé)

```bash
# Construire et démarrer le service
docker-compose up --build

# En arrière-plan
docker-compose up -d --build
```

### 3. Démarrage manuel (pour développement)

```bash
# Installer les dépendances
pip install -r requirements.txt

# Générer les fichiers gRPC
python generate_grpc.py

# Démarrer le serveur
python ocr_server.py
```

## 🧪 Tests

### Test simple avec l'image par défaut

```bash
# Test recto 2018 (par défaut)
python test_client.py data/ID\ Card\ Kengali\ Fegue\ Pacome_1.jpg

# Test avec thinking mode
python test_client.py data/ID\ Card\ Kengali\ Fegue\ Pacome_1.jpg --thinking

# Test verso 2018
python test_client.py data/ID\ Card\ Kengali\ Fegue\ Pacome_2.jpg --side verso

# Test carte 2025
python test_client.py mon_image.jpg --version 2025 --side recto
```

### Options du client de test

```bash
python test_client.py --help

# Options disponibles:
# --version, -v    : "2018" ou "2025" (défaut: 2018)
# --side, -s       : "recto" ou "verso" (défaut: recto)
# --thinking, -t   : Activer le mode thinking
# --host           : Adresse du serveur (défaut: localhost)
# --port           : Port du serveur (défaut: 50051)
```

## ⚙️ Configuration

Le fichier `config.yaml` permet de configurer le service :

```yaml
model:
  # Type de modèle: "finetune" ou "lora"
  type: "finetune"
  
  # Pour modèle fine-tuné
  finetune_path: "./models/finetunes/qwen3-0.6b-lora-cni-2018-front"
  
  # Pour modèle LoRA (si type = "lora")
  base_path: "./models/Qwen/Qwen3-0.6B"
  lora_adapter_path: "./models/finetunes/qwen3-0.6b-cni-lora/checkpoint-938"

server:
  host: "0.0.0.0"
  port: 50051
```

### Changement de modèle

1. **Modèle Fine-tuné** (actuel):
   ```yaml
   model:
     type: "finetune"
     finetune_path: "./models/finetunes/qwen3-0.6b-lora-cni-2018-front"
   ```

2. **Modèle LoRA**:
   ```yaml
   model:
     type: "lora"
     base_path: "./models/Qwen/Qwen3-0.6B"
     lora_adapter_path: "./models/finetunes/qwen3-0.6b-cni-lora/checkpoint-938"
   ```

## 📊 Formats de Données Extraites

### Carte 2018 - RECTO
```json
{
  "nom_surname": "KENGALI FEGUE",
  "prenom_given_name": "Pacome",
  "date_of_birth": "15.03.1990",
  "lieu_of_birth": "Yaoundé",
  "sex": "M",
  "taille": 1.75,
  "profession": "Ingénieur"
}
```

### Carte 2018 - VERSO
```json
{
  "pere_father": "KENGALI Jean",
  "mere_mother": "FEGUE Marie",
  "sp_sm": "123456",
  "date_of_issue": "01.01.2018",
  "date_of_expiration": "01.01.2028",
  "identifiant_unique": 20181234567890123,
  "numero_de_carte": 123456789,
  "authorité": "Martin MBARGA NGUELE"
}
```

## 🐛 Dépannage

### Erreurs communes

1. **Erreur de connexion gRPC**
   ```
   ❌ Erreur gRPC: failed to connect
   ```
   - Vérifiez que le serveur est démarré
   - Vérifiez le port (défaut: 50051)

2. **Modèle non trouvé**
   ```
   ❌ Erreur: Model path not found
   ```
   - Vérifiez le chemin dans `config.yaml`
   - Assurez-vous que les modèles sont présents

3. **Fichiers gRPC manquants**
   ```
   ❌ ModuleNotFoundError: No module named 'ocr_pb2'
   ```
   - Exécutez: `python generate_grpc.py`

### Logs

- **Docker**: `docker-compose logs -f ocr-service`
- **Manuel**: Les logs s'affichent directement dans le terminal

### Vérification du service

```bash
# Test de santé simple
python -c "
import grpc
import ocr_pb2_grpc

try:
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = ocr_pb2_grpc.OCRServiceStub(channel)
        print('✅ Service OCR accessible')
except:
    print('❌ Service OCR inaccessible')
"
```

## 🔧 Architecture

```
[Client] → [gRPC] → [OCR Server] → [Modèle Qwen] → [JSON]
                         ↓
                   [PaddleOCR] → [Texte brut]
```

- **Load-Once**: Le modèle est chargé une seule fois au démarrage
- **Concurrent**: Plusieurs requêtes simultanées supportées
- **Thinking Mode**: Prompts avec raisonnement explicite

## 📁 Structure du Projet

```
ocr-poc/
├── config.yaml              # Configuration du service
├── ocr_server.py            # Serveur gRPC principal
├── ocr_service.proto        # Définition du service gRPC
├── test_client.py           # Client de test
├── generate_grpc.py         # Générateur des fichiers gRPC
├── Dockerfile               # Image Docker
├── docker-compose.yml       # Orchestration Docker
├── requirements.txt         # Dépendances Python
├── ocr/                     # Module OCR
│   ├── id_card_data_extractor.py
│   ├── llm_post_processor.py
│   └── ...
├── models/                  # Modèles ML
└── data/                    # Données de test
```

## 📈 Performance

- **Temps de démarrage**: ~30-60 secondes (chargement du modèle)
- **Temps d'inférence**: ~2-5 secondes par image
- **Mémoire**: ~4-8 GB (selon le modèle)
- **Concurrent**: Supporté (1 worker par défaut pour éviter le rechargement)

---

✅ **Prêt à l'usage!** Le service est configuré avec le modèle fine-tuné pour des résultats optimaux.