#!/usr/bin/env python3
"""
Script de démarrage pour le service OCR
Lance l'API REST avec OCR intégré
"""

import subprocess
import sys
import os

def main():
    print("=" * 60)
    print("ID CARD OCR - CARTE D'IDENTITÉ CAMEROUNAISE")
    print("=" * 60)
    print()
    
    # Vérifier les fichiers nécessaires
    required_files = ["api_server.py", "config.yaml"]
    for file in required_files:
        if not os.path.exists(file):
            print(f"Fichier manquant: {file}")
            return 1
    
    print("Tous les fichiers requis sont présents")
    print()
    
    try:
        print("Démarrage du service OCR...")
        print()
        print("=" * 60)
        print("SERVICE DÉMARRÉ AVEC SUCCÈS !")
        print("=" * 60)
        print("Interface web: http://localhost:8080")
        print("Santé de l'API: http://localhost:8080/api/health")
        print("API REST: http://localhost:8080/api/extract")
        print()
        print("Appuyez sur Ctrl+C pour arrêter le service")
        print("=" * 60)
        print()
        
        # Lancer l'API REST avec Gunicorn
        subprocess.run(["gunicorn", "--config", "gunicorn.conf.py", "api_server:app"])
        
    except KeyboardInterrupt:
        print("\nArrêt du service...")
        return 0
    except Exception as e:
        print(f"\nErreur: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())