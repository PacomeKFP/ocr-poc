#!/usr/bin/env python3
"""
Script pour générer les fichiers gRPC Python à partir du fichier .proto
"""

import subprocess
import sys
from pathlib import Path

def generate_grpc_files():
    """Génère les fichiers Python gRPC à partir du fichier .proto"""
    
    proto_file = "ocr_service.proto"
    
    if not Path(proto_file).exists():
        print(f"❌ Erreur: Fichier {proto_file} introuvable")
        return False
    
    print("🔧 Génération des fichiers gRPC...")
    
    try:
        # Exécuter la commande protoc
        cmd = [
            sys.executable, "-m", "grpc_tools.protoc",
            "--python_out=.",
            "--grpc_python_out=.",
            "--proto_path=.",
            proto_file
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Fichiers gRPC générés avec succès:")
            print("  - ocr_pb2.py")
            print("  - ocr_pb2_grpc.py")
            return True
        else:
            print(f"❌ Erreur lors de la génération:")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    if generate_grpc_files():
        print("✅ Prêt pour les tests!")
    else:
        print("❌ Génération échouée")
        sys.exit(1)