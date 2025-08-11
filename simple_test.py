#!/usr/bin/env python3
"""
Test simple pour vérifier que l'API fonctionne
"""

import requests
import time

def test_api():
    """Test simple de l'API"""
    print("Test de l'API OCR...")
    
    # Test 1: Health check
    try:
        print("1. Test health endpoint...")
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Service status: {data.get('status', 'unknown')}")
        
    except requests.exceptions.ConnectionError:
        print("   Erreur: API non disponible (serveur non demarre?)")
        return False
    except Exception as e:
        print(f"   Erreur: {e}")
        return False
    
    print("\nTest termine avec succes!")
    return True

if __name__ == '__main__':
    success = test_api()
    exit(0 if success else 1)