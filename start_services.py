#!/usr/bin/env python3
"""
Script de démarrage pour les services OCR
Lance le serveur gRPC et l'API REST
"""

import subprocess
import sys
import time
import os
import signal
import threading

def run_grpc_server():
    """Lance le serveur gRPC"""
    print("Démarrage du serveur gRPC...")
    try:
        process = subprocess.Popen([sys.executable, "ocr_server.py"], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.STDOUT,
                                 universal_newlines=True,
                                 bufsize=1)
        
        # Afficher les logs du serveur gRPC
        for line in process.stdout:
            print(f"[gRPC] {line.strip()}")
            
    except Exception as e:
        print(f"Erreur lors du démarrage du serveur gRPC: {e}")

def run_api_server():
    """Lance l'API REST Flask"""
    print("Démarrage de l'API REST...")
    try:
        # Attendre que le serveur gRPC soit prêt
        time.sleep(5)
        
        process = subprocess.Popen([sys.executable, "api_server.py"], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.STDOUT,
                                 universal_newlines=True,
                                 bufsize=1)
        
        # Afficher les logs de l'API REST
        for line in process.stdout:
            print(f"[API] {line.strip()}")
            
    except Exception as e:
        print(f"Erreur lors du démarrage de l'API REST: {e}")

def main():
    print("=" * 60)
    print("SERVICE OCR - CARTE D'IDENTITE CAMEROUNAISE")
    print("=" * 60)
    print()
    
    # Vérifier les fichiers nécessaires
    required_files = ["ocr_server.py", "api_server.py", "config.yaml"]
    for file in required_files:
        if not os.path.exists(file):
            print(f"Fichier manquant: {file}")
            return 1
    
    print("Tous les fichiers requis sont presents")
    print()
    
    try:
        # Lancer les deux services dans des threads séparés
        grpc_thread = threading.Thread(target=run_grpc_server, daemon=True)
        api_thread = threading.Thread(target=run_api_server, daemon=True)
        
        grpc_thread.start()
        api_thread.start()
        
        print()
        print("=" * 60)
        print("SERVICES DEMARRES AVEC SUCCES !")
        print("=" * 60)
        print("Interface web: http://localhost:5000")
        print("Serveur gRPC: localhost:50051")
        print("Sante de l'API: http://localhost:5000/api/health")
        print()
        print("Appuyez sur Ctrl+C pour arreter les services")
        print("=" * 60)
        
        # Attendre indéfiniment
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nArret des services...")
        return 0
    except Exception as e:
        print(f"\nErreur: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())