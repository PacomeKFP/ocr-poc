# Guide d'Intégration LoRA - Qwen3-0.6B Finetunés pour l'OCR

## Table des Matières
1. [Introduction à LoRA](#introduction-à-lora)
2. [Analyse du Modèle Finetuné](#analyse-du-modèle-finetuné)
3. [Requirements Techniques](#requirements-techniques)
4. [Plan d'Intégration](#plan-dintégration)
5. [Implémentation Pratique](#implémentation-pratique)
6. [Optimisation et Performance](#optimisation-et-performance)
7. [Troubleshooting](#troubleshooting)

---

## Introduction à LoRA

### Qu'est-ce que LoRA ?

**LoRA (Low-Rank Adaptation)** est une technique d'adaptation efficace des modèles de langage pré-entraînés qui permet de :

- **Réduire drastiquement** les paramètres entraînables (de ~600M à ~1M paramètres)
- **Maintenir les performances** du modèle original
- **Accélérer l'entraînement** et réduire la consommation mémoire
- **Faciliter le déploiement** avec des adapters légers

### Principe de Fonctionnement

LoRA décompose les matrices de poids `W` des couches d'attention en deux matrices de rang faible :

```
W = W₀ + BA
```

Où :
- `W₀` : Matrice de poids pré-entraînée (gelée)
- `B` : Matrice down-projection (r × d)
- `A` : Matrice up-projection (k × r)
- `r` : Rang de décomposition (hyperparamètre clé)

### Avantages de LoRA

1. **Efficacité Mémoire** : Seules les matrices B et A sont entraînées
2. **Modularité** : Plusieurs adapters peuvent être échangés sur le même modèle de base
3. **Préservation** : Le modèle original reste intact
4. **Rapidité** : Entraînement et inférence accélérés

---

## Analyse du Modèle Finetuné

### Caractéristiques Identifiées

D'après l'analyse du checkpoint `qwen3-0.6b-cni-lora/checkpoint-938` :

```json
{
  "base_model_name_or_path": "Qwen/Qwen3-0.6B",
  "peft_type": "LORA",
  "r": 16,                    // Rang de décomposition
  "lora_alpha": 32,           // Facteur de mise à l'échelle
  "lora_dropout": 0.05,       // Dropout pour régularisation
  "target_modules": [
    "v_proj",                 // Projection des valeurs
    "q_proj"                  // Projection des requêtes
  ],
  "task_type": "CAUSAL_LM"
}
```

### Spécifications Techniques

- **Modèle de Base** : Qwen3-0.6B (602M paramètres)
- **Adapters LoRA** : ~1.3M paramètres supplémentaires
- **Cibles** : Couches d'attention (q_proj, v_proj)
- **Entraînement** : 938 steps, 1 époque complète
- **Framework** : PEFT 0.16.0

---

## Requirements Techniques

### Dépendances Python

```bash
# Core ML frameworks
torch>=1.13.0
transformers>=4.30.0
accelerate>=0.20.0

# LoRA et Fine-tuning
peft>=0.16.0
bitsandbytes>=0.39.0  # Pour la quantification

# OCR et Vision
paddlepaddle>=2.5.0
paddleocr>=2.7.0
Pillow>=9.0.0

# Web Framework
Flask>=2.3.3

# Utilitaires
safetensors>=0.3.0
huggingface-hub>=0.15.0
```

### Configuration Système

#### Minimum Requis
- **RAM** : 8GB (CPU) / 6GB VRAM (GPU)
- **Stockage** : 2GB pour le modèle de base + 10MB pour l'adapter
- **CPU** : 4 cores minimum

#### Recommandé
- **RAM** : 16GB (CPU) / 8GB VRAM (GPU)
- **GPU** : NVIDIA RTX 3060 ou supérieur
- **CPU** : 8 cores avec AVX2

---

## Plan d'Intégration

### Phase 1 : Préparation de l'Infrastructure

1. **Installation des Dépendances**
   ```bash
   pip install -r requirements_lora.txt
   ```

2. **Vérification de la Compatibilité**
   - Validation des versions PyTorch/CUDA
   - Test de chargement PEFT
   - Vérification des chemins des modèles

3. **Organisation des Modèles**
   ```
   models/
   ├── Qwen/Qwen3-0.6B/              # Modèle de base
   └── finetunes/
       └── qwen3-0.6b-cni-lora/      # Adapter LoRA
           └── checkpoint-938/
   ```

### Phase 2 : Modification du Code

1. **Adapter le LLMPostProcessor**
   - Intégration de PEFT
   - Chargement du modèle de base + adapter
   - Configuration des paramètres LoRA

2. **Extension de IDCardDataExtractor**
   - Support des modèles finecutés
   - Sélection dynamique des modèles
   - Gestion des erreurs spécifiques

3. **Interface Utilisateur**
   - Dropdown pour sélection du modèle
   - Indicateurs de performance
   - Métriques de confiance

### Phase 3 : Tests et Validation

1. **Tests Unitaires**
   - Chargement des modèles
   - Inférence avec adapters
   - Comparaison des performances

2. **Tests d'Intégration**
   - Pipeline complet OCR + LoRA
   - Interface web avec nouveaux modèles
   - Gestion des erreurs

3. **Benchmarking**
   - Comparaison modèle de base vs finetuné
   - Métriques de précision
   - Performance temporelle

### Phase 4 : Déploiement

1. **Optimisation**
   - Configuration de la quantification
   - Optimisation mémoire
   - Cache des modèles

2. **Monitoring**
   - Métriques de performance
   - Suivi des erreurs
   - Logs détaillés

---

## Implémentation Pratique

### 1. Nouveau LLMPostProcessor avec Support LoRA

```python
# ocr/llm_post_processor_lora.py
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel, PeftConfig
import logging

class LLMPostProcessorLoRA:
    def __init__(self, base_model_path, adapter_path=None):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.base_model_path = base_model_path
        self.adapter_path = adapter_path
        
        # Charger le tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            base_model_path, 
            trust_remote_code=True
        )
        
        # Charger le modèle de base
        self.base_model = AutoModelForCausalLM.from_pretrained(
            base_model_path,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            low_cpu_mem_usage=True,
            trust_remote_code=True
        )
        
        # Charger l'adapter LoRA si spécifié
        if adapter_path:
            self.model = PeftModel.from_pretrained(
                self.base_model, 
                adapter_path
            )
            logging.info(f"LoRA adapter loaded from {adapter_path}")
        else:
            self.model = self.base_model
            
        self.model.to(self.device)
        
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

    def execute(self, instructions):
        """Execute inference with LoRA adapter"""
        inputs = self.tokenizer(instructions, return_tensors="pt").to(self.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=200,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id
            )
        
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        generated_text = response[len(instructions):].strip()
        
        # Parse JSON
        first_opening = generated_text.find("{")
        first_closure = generated_text.find("}")
        
        if first_closure != -1 and first_opening != -1 and first_closure > first_opening:
            json_text = generated_text[first_opening:first_closure + 1]
            try:
                parsed_json = json.loads(json_text)
                return generated_text, parsed_json
            except json.JSONDecodeError:
                return generated_text, None
        
        return generated_text, None
```

### 2. Configuration des Modèles

```python
# config/model_config.py
MODEL_CONFIGS = {
    "qwen3-0.6b-base": {
        "path": "./models/Qwen/Qwen3-0.6B",
        "adapter": None,
        "description": "Modèle de base Qwen3-0.6B"
    },
    "qwen3-0.6b-cni-lora": {
        "path": "./models/Qwen/Qwen3-0.6B",
        "adapter": "./models/finetunes/qwen3-0.6b-cni-lora/checkpoint-938",
        "description": "Qwen3-0.6B finetuné pour cartes d'identité camerounaises"
    }
}
```

### 3. Interface Web Étendue

```python
# Ajout dans app.py
@app.route('/models', methods=['GET'])
def get_available_models():
    return jsonify({
        "models": [
            {
                "id": key,
                "name": config["description"],
                "has_adapter": config["adapter"] is not None
            }
            for key, config in MODEL_CONFIGS.items()
        ]
    })

@app.route('/upload', methods=['POST'])
def upload_file():
    # ... code existant ...
    
    model_id = request.form.get('model', 'qwen3-0.6b-base')
    config = MODEL_CONFIGS.get(model_id)
    
    if config:
        # Charger le modèle approprié
        processor = LLMPostProcessorLoRA(
            config["path"], 
            config["adapter"]
        )
        # ... reste du code ...
```

### 4. Requirements Mis à Jour

```txt
# requirements_lora.txt
torch>=1.13.0
transformers>=4.30.0
peft>=0.16.0
accelerate>=0.20.0
bitsandbytes>=0.39.0
safetensors>=0.3.0
paddlepaddle>=2.5.0
paddleocr>=2.7.0
Flask>=2.3.3
Pillow>=9.0.0
huggingface-hub>=0.15.0
```

---

## Optimisation et Performance

### Quantification pour Production

```python
from transformers import BitsAndBytesConfig

# Configuration 4-bit pour réduire la mémoire
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

model = AutoModelForCausalLM.from_pretrained(
    model_path,
    quantization_config=bnb_config,
    trust_remote_code=True
)
```

### Cache et Optimisation Mémoire

```python
# Cache des modèles en mémoire
model_cache = {}

def get_cached_model(model_id):
    if model_id not in model_cache:
        config = MODEL_CONFIGS[model_id]
        model_cache[model_id] = LLMPostProcessorLoRA(
            config["path"], 
            config["adapter"]
        )
    return model_cache[model_id]
```

---

## Troubleshooting

### Erreurs Communes

1. **CUDA Out of Memory**
   ```python
   # Solution : Utiliser la quantification 4-bit
   # Ou forcer l'utilisation du CPU
   device = "cpu"
   ```

2. **Adapter Non Compatible**
   ```python
   # Vérifier la compatibilité des versions
   peft_config = PeftConfig.from_pretrained(adapter_path)
   assert peft_config.base_model_name_or_path == base_model_path
   ```

3. **Performance Dégradée**
   ```python
   # Optimiser les paramètres de génération
   generation_config = {
       "max_new_tokens": 150,  # Réduire si nécessaire
       "temperature": 0.3,     # Plus déterministe
       "do_sample": False      # Génération greedy
   }
   ```

### Monitoring et Debugging

```python
import time
import psutil

def monitor_inference(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.virtual_memory().used
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        end_memory = psutil.virtual_memory().used
        
        logging.info(f"Inference time: {end_time - start_time:.2f}s")
        logging.info(f"Memory usage: {(end_memory - start_memory) / 1024**2:.2f}MB")
        
        return result
    return wrapper
```

---

## Conclusion

Cette intégration de LoRA permettra d'améliorer significativement la précision de l'extraction OCR pour les cartes d'identité camerounaises tout en maintenant une efficacité computationnelle optimale. Le modèle finetuné devrait offrir de meilleures performances sur les spécificités locales du format des documents.

### Prochaines Étapes

1. **Implémentation** du LLMPostProcessorLoRA
2. **Tests comparatifs** base vs finetuné
3. **Optimisation** des hyperparamètres d'inférence
4. **Évaluation** sur un dataset de validation
5. **Déploiement** en production avec monitoring

---

*Guide créé pour l'intégration du modèle Qwen3-0.6B finetuné avec LoRA dans le système OCR de cartes d'identité camerounaises.*