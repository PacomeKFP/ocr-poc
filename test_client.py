#!/usr/bin/env python3
"""
Client de test simple pour le service OCR gRPC
"""

import grpc
import ocr_service_pb2
import ocr_service_pb2_grpc
import json
import argparse
from pathlib import Path

def test_ocr_service(image_path, version="2018", side="recto", thinking=False, host="localhost", port=50051):
    """
    Teste le service OCR avec une image
    
    Args:
        image_path: Chemin vers l'image à analyser
        version: Version de la carte ("2018" ou "2025")
        side: Face de la carte ("recto" ou "verso")
        thinking: Activer le mode thinking (True/False)
        host: Adresse du serveur
        port: Port du serveur
    """
    
    # Vérifier que le fichier existe
    if not Path(image_path).exists():
        print(f"❌ Erreur: Fichier {image_path} introuvable")
        return False
    
    # Lire l'image
    with open(image_path, 'rb') as f:
        image_data = f.read()
    
    print(f"📷 Image: {image_path}")
    print(f"📋 Paramètres: version={version}, side={side}, thinking={thinking}")
    print(f"🌐 Serveur: {host}:{port}")
    print("-" * 50)
    
    try:
        # Connexion au serveur gRPC
        with grpc.insecure_channel(f'{host}:{port}') as channel:
            stub = ocr_service_pb2_grpc.OCRServiceStub(channel)
            
            # Créer la requête
            request = ocr_service_pb2.OCRRequest(
                image_data=image_data,
                version=version,
                side=side,
                thinking_mode=thinking
            )
            
            print("🚀 Envoi de la requête...")
            
            # Appeler le service
            response = stub.ExtractData(request)
            
            if response.success:
                print("✅ Extraction réussie!\n")
                
                print("📝 Texte OCR brut:")
                print(response.raw_text)
                print("\n" + "="*50 + "\n")
                
                print("📊 Données extraites:")
                try:
                    extracted_json = json.loads(response.extracted_data)
                    print(json.dumps(extracted_json, indent=2, ensure_ascii=False))
                except json.JSONDecodeError:
                    print(response.extracted_data)
                
                return True
            else:
                print(f"❌ Erreur: {response.error}")
                return False
                
    except grpc.RpcError as e:
        print(f"❌ Erreur gRPC: {e}")
        print("💡 Vérifiez que le serveur OCR est démarré")
        return False
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Client de test pour le service OCR")
    parser.add_argument("image", help="Chemin vers l'image à analyser")
    parser.add_argument("--version", "-v", choices=["2018", "2025"], default="2018", 
                       help="Version de la carte (défaut: 2018)")
    parser.add_argument("--side", "-s", choices=["recto", "verso"], default="recto",
                       help="Face de la carte (défaut: recto)")
    parser.add_argument("--thinking", "-t", action="store_true",
                       help="Activer le mode thinking")
    parser.add_argument("--host", default="localhost", help="Adresse du serveur (défaut: localhost)")
    parser.add_argument("--port", type=int, default=50051, help="Port du serveur (défaut: 50051)")
    
    args = parser.parse_args()
    
    print("🔍 Test du service OCR gRPC")
    print("="*50)
    
    success = test_ocr_service(
        image_path=args.image,
        version=args.version,
        side=args.side,
        thinking=args.thinking,
        host=args.host,
        port=args.port
    )
    
    if success:
        print("\n✅ Test réussi!")
    else:
        print("\n❌ Test échoué!")
        exit(1)

if __name__ == "__main__":
    main()