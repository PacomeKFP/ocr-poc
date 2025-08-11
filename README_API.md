# OCR Pro - Système d'Extraction Intelligente

> Interface moderne avec intelligence artificielle pour l'extraction de données des cartes d'identité camerounaises

## Démarrage rapide

**Nouveau design Jony Ive avec couleurs Orange et gestion d'erreurs avancée !**

### 1. Installation des dépendances
```bash
pip install -r requirements.txt
```

### 2. Génération des fichiers gRPC (si nécessaire)
```bash
python generate_grpc.py
```

### 3. Démarrage des services

#### Option A: Démarrage automatique (recommandé)
```bash
python start_services.py
```

#### Option B: Démarrage manuel
Terminal 1 - Serveur gRPC:
```bash
python ocr_server.py
```

Terminal 2 - API REST:
```bash
python api_server.py
```

### 4. Accès à l'interface web
Ouvrez votre navigateur à: http://localhost:5000

## Fonctionnalités

### Interface Redesignée (Style Jony Ive)
- **Design minimaliste** inspiré d'Apple avec couleurs Orange
- **Interface fluide** avec animations et transitions
- **Indicateur de chargement premium** avec progression détaillée
- **Backdrop blur** et effets visuels modernes
- **Responsive design** optimisé mobile/desktop

### Robustesse et Monitoring
- **Logs détaillés** avec rotation automatique
- **Recovery automatique** avec retry progressif (3 tentatives)
- **Gestion d'erreurs intelligente** avec codes d'erreur spécifiques
- **Monitoring temps réel** avec métriques de performance
- **Health checks** complets avec indicateurs visuels
- **Timeout adaptatif** et gestion des connexions

### Fonctionnalités Métier
- **Support cartes 2018 et 2025** (recto/verso)
- **Mode haute précision** (thinking mode)
- **Extraction structurée** en JSON
- **Validation côté client et serveur**

## Performance et Monitoring

### Nouvelles métriques disponibles
- **Temps de traitement** par requête
- **Nombre de retries** automatiques
- **Taux de succès** global
- **Health status** temps réel

## API Endpoints Améliorés

### POST `/api/extract`
Extrait les données d'une carte d'identité

**Paramètres:**
- `image`: fichier image (JPEG, PNG, etc.)
- `version`: "2018" ou "2025"
- `side`: "recto" ou "verso"  
- `thinking_mode`: true/false (optionnel)

**Réponse améliorée:**
```json
{
    "success": true,
    "raw_text": "texte OCR brut...",
    "extracted_data": {
        "nom_surname": "KENGALI",
        "prenom_given_name": "Fegue Pacome",
        ...
    },
    "meta": {
        "processing_time": 15.3,
        "retry_count": 0,
        "timestamp": "2024-01-15T10:30:00"
    }
}
```

**Gestion d'erreurs robuste:**
```json
{
    "success": false,
    "error": "Service temporairement indisponible",
    "error_code": "SERVICE_UNAVAILABLE",
    "meta": {
        "retry_count": 3,
        "can_retry": false,
        "timestamp": "2024-01-15T10:30:00"
    }
}
```

### GET `/api/health`
Vérifie l'état détaillé des services

**Réponse complète:**
```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00",
    "services": {
        "api": {
            "status": "running",
            "uptime": 3600.5
        },
        "grpc_server": {
            "status": "connected",
            "host": "localhost:50051"
        }
    },
    "metrics": {
        "total_requests": 1247,
        "successful_requests": 1198,
        "failed_requests": 49,
        "success_rate_percent": 96.1,
        "average_processing_time_seconds": 12.4
    },
    "system": {
        "disk_space_mb": 15240.8,
        "log_file_size_mb": 45.2
    }
}
```

## Configuration

Le fichier `config.yaml` contient la configuration des modèles et du serveur.

## Structure du projet

```
ocr-poc/
├── api_server.py          # API REST Flask avec logs avancés
├── ocr_server.py          # Serveur gRPC
├── start_services.py      # Script de démarrage
├── test_system.py         # Tests de robustesse
├── simple_test.py         # Test simple
├── templates/
│   └── index.html         # Interface web redesignée
├── logs/                  # Dossier des logs (auto-créé)
├── uploads/               # Fichiers uploadés (auto-créé)
├── config.yaml            # Configuration
├── requirements.txt       # Dépendances
└── README_API.md         # Cette documentation
```

## Fichiers de logs générés

- `api_server.log` - Logs détaillés de l'API
- `api_metrics.log` - Métriques de performance
- `logs/` - Dossier pour logs additionnels

## Design et UX (Style Jony Ive)

### Palette de couleurs Orange
- **Primary**: `#ff6600` (Orange signature)
- **Secondary**: `#e55a00` (Orange hover)
- **Background**: `#f5f5f7` (Gris Apple)
- **Text**: `#1d1d1f` (Noir Apple)
- **Subtle**: `#86868b` (Gris secondaire)

### Animations et interactions
- **Cubic-bezier easing** pour fluidité naturelle
- **Backdrop blur** 20px pour profondeur
- **Box-shadows** subtiles avec transparence
- **Border-radius** 12px+ pour modernité
- **Letter-spacing** négatif pour lisibilité

### Indicateur de chargement premium
- **Overlay translucide** avec blur
- **Progression visuelle** par étapes
- **Numérotation contextuelles** pour chaque phase
- **Messages informatifs** en temps réel

## Monitoring et Debugging

### Logs détaillés
```bash
# Logs en temps réel
tail -f api_server.log

# Métriques de performance  
tail -f api_metrics.log
```

### Health check avancé
```bash
# Vérification complète
curl http://localhost:5000/api/health | jq

# Test simple
python simple_test.py

# Tests de robustesse complets
python test_system.py
```

### Codes d'erreur système
- `NO_FILE` - Aucun fichier fourni
- `INVALID_FILE_TYPE` - Type de fichier non supporté
- `INVALID_VERSION` - Version invalide (2018/2025)
- `INVALID_SIDE` - Côté invalide (recto/verso)
- `SERVICE_UNAVAILABLE` - Service gRPC indisponible
- `TEMPORARY_ERROR` - Erreur temporaire (retry possible)
- `PROCESSING_ERROR` - Erreur durant l'extraction
- `INTERNAL_ERROR` - Erreur serveur critique

## Dépannage

1. **Service indisponible**: Vérifiez `api_server.log` pour les détails
2. **gRPC timeout**: Le retry automatique se déclenche (3 tentatives)
3. **Modèles manquants**: Vérifiez les chemins dans `config.yaml`
4. **Ports occupés**: 5000 (API) et 50051 (gRPC) requis
5. **Logs volumineux**: Rotation automatique implémentée

## Sécurité

- **Validation stricte** des types de fichiers
- **Limitation uploads** 16MB max
- **Nettoyage automatique** des fichiers temporaires
- **Sanitisation** des noms de fichiers
- **Logs sécurisés** sans données sensibles
- **Timeout protection** contre les attaques DoS
- **Error handling** sans exposition d'informations système

## Performance et Scalabilité

### Métriques monitorées
- Nombre total de requêtes
- Taux de succès/échec
- Temps de traitement moyen
- Nombre de retries
- Espace disque disponible
- Taille des logs

### Optimisations
- **Connection pooling** pour gRPC
- **Retry progressif** (5s, 10s, 20s)
- **Timeout adaptatif** (300s max)
- **Memory cleanup** automatique
- **Log rotation** pour éviter l'accumulation

## États du système

- **Healthy**: Tous services opérationnels
- **Degraded**: Service partiel (API OK, gRPC KO)
- **Unhealthy**: Services indisponibles

Chaque état est visualisé dans l'interface avec indicateurs colorés.