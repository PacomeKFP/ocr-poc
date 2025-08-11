import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher
import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher


class CNIExtractor18B:
    """
    Extracteur pour le verso de CNI camerounaise utilisant une approche par élimination
    avec détection floue des ancres.
    """

    def __init__(self, quality_threshold: float = 0.5, similarity_threshold: float = 0.70, debug: bool = True):
        """
        Initialise l'extracteur pour le verso.

        Args:
            quality_threshold: Seuil minimal de qualité OCR pour procéder
            similarity_threshold: Seuil de similarité pour la détection des ancres
            debug: Active les logs de débogage
        """
        self.quality_threshold = quality_threshold
        self.similarity_threshold = similarity_threshold
        self.debug = debug

        # Ancres possibles pour chaque champ du verso
        self.anchors = {
            'pere': ['PERE', 'FATHER', 'PERE/FATHER'],
            'mere': ['MERE', 'MOTHER', 'MERE/MOTHER'],
            'date_delivrance': ['DATE DE DELIVRANCE', 'DATE OF ISSUE', 
                               'DATE DE DELIVRANCEI', 'DATEOFISSUE'],
            'date_expiration': ['DATE D\'EXPIRATION', 'DATE OF EXPIRY',
                              'DATED\'EXPIRATION', 'DATEOF EXPIRY'],
            'adresse': ['ADRESSE', 'ADDRESS', 'ADRESSE/ADDRESS'],
            'poste_identification': ['POSTE D\'IDENTIFICATION', 'IDENTIFICATION POST',
                                    'POSTE DIDENTIFICATION', 'POSTE DIDENTIFICATIONA'],
            'identifiant_unique': ['IDENTIFIANT UNIQUE', 'UNIQUE IDENTIFIER',
                                  'IDENTIFIANTUNIQUE', 'UNIQUEIDENTIFIER',
                                  'IDENTIFIANTUNIQUEI', 'UNIQUEIDENTIFIERI'],
            'autorite': ['AUTORITE', 'AUTHORITY', 'AUTORITE/AUTHORITY']
        }

        # Tous les labels possibles (pour filtrage)
        self.all_labels = set()
        for labels in self.anchors.values():
            self.all_labels.update(labels)
        self.all_labels.update(['S.P.', 'S.M.', 'S.P./S.M.', 
                                'CAMEROUN', 'CAMEROON'])

    def log(self, message: str, level: str = "INFO"):
        """Affiche un message de log si le mode debug est activé."""
        if self.debug:
            print(f"[{level}] {message}")

    def assess_quality(self, ocr_data: Dict) -> Tuple[bool, float]:
        """
        Évalue la qualité globale des données OCR.

        Returns:
            (peut_continuer, score_qualite)
        """
        self.log("=== ÉVALUATION DE LA QUALITÉ ===")

        scores = ocr_data.get('rec_scores', [])
        texts = ocr_data.get('rec_texts', [])

        if not scores or not texts:
            self.log("Pas de données OCR", "ERROR")
            return False, 0.0

        # Filtrer les scores valides (> 0)
        valid_scores = [s for s in scores if s > 0]

        if not valid_scores:
            self.log("Aucun score valide", "ERROR")
            return False, 0.0

        # Calculer le score moyen
        avg_score = sum(valid_scores) / len(valid_scores)

        # Compter les éléments de bonne qualité
        good_quality = sum(1 for s in scores if s > 0.7)

        self.log(f"Score moyen: {avg_score:.2f}")
        self.log(f"Éléments de bonne qualité (>0.7): {good_quality}/{len(scores)}")
        self.log(f"Éléments valides: {len(valid_scores)}")

        # Au moins 5 éléments détectés pour le verso
        can_proceed = (len(valid_scores) >= 5 and 
                      avg_score >= self.quality_threshold and
                      good_quality >= 3)

        self.log(f"Peut continuer: {can_proceed}")

        return can_proceed, avg_score

    def preprocess(self, texts: List[str], scores: List[float],
                  polygons: List) -> List[Tuple[str, float, List]]:
        """
        Prétraite les données OCR en filtrant le bruit.
        Pour le moment, traitement minimal comme demandé.
        """
        self.log("=== PRÉPROCESSING (MINIMAL) ===")
        processed = []

        for i, (text, score, polygon) in enumerate(zip(texts, scores, polygons)):
            # Filtrer les scores très faibles
            if score < 0.3:
                self.log(f"  Filtré (score faible): '{text}' (score={score:.2f})", "DEBUG")
                continue

            # Filtrer les textes vides
            text = text.strip()
            if not text:
                self.log(f"  Filtré (texte vide): index {i}", "DEBUG")
                continue

            # Filtrer les caractères non-latins isolés (鸡, 川)
            if len(text) <= 2:
                if any(ord(c) > 127 for c in text):
                    self.log(f"  Filtré (caractère non-latin): '{text}'", "DEBUG")
                    continue

            processed.append((text, score, polygon))
            self.log(f"  Gardé: '{text}' (score={score:.2f})")

        self.log(f"Éléments après préprocessing: {len(processed)}/{len(texts)}")

        return processed

    def similarity_score(self, str1: str, str2: str) -> float:
        """
        Calcule le score de similarité entre deux chaînes.
        """
        s1 = str1.upper().strip()
        s2 = str2.upper().strip()

        base_score = SequenceMatcher(None, s1, s2).ratio()

        # Bonus pour préfixe identique
        prefix_match = 0
        for i in range(min(4, len(s1), len(s2))):
            if s1[i] == s2[i]:
                prefix_match += 1
            else:
                break

        final_score = base_score + (prefix_match * 0.1 * (1 - base_score))

        return min(final_score, 1.0)

    def extract_fixed_format_fields(self, data: List[Tuple[str, float, List]]) -> Dict:
        """
        Extrait les champs à format fixe (dates, numéros).
        """
        self.log("=== EXTRACTION DES CHAMPS À FORMAT FIXE ===")

        results = {
            'date_delivrance': None,
            'date_expiration': None,
            'identifiant_unique': None,
            'numero_cni': None,
            'poste_code': None
        }
        indices_to_remove = []

        # Patterns de détection
        date_pattern = re.compile(r'^\d{1,2}[./]\d{1,2}[./]\d{4}$')
        id_unique_pattern = re.compile(r'^\d{15,20}$')  # Identifiant unique long
        numero_pattern = re.compile(r'^\d{9}$')  # Numéro CNI (9 chiffres)
        poste_pattern = re.compile(r'^[A-Z]{2}\d{2}$')  # Code poste (ex: LT02)

        dates_found = []
        
        for idx, (text, score, polygon) in enumerate(data):
            # Dates (on en attend 2 : délivrance et expiration)
            if date_pattern.match(text):
                dates_found.append((text, idx))
                self.log(f"  Date trouvée: '{text}' à l'index {idx}")
                indices_to_remove.append(idx)
                continue
            
            # Identifiant unique
            if not results['identifiant_unique'] and id_unique_pattern.match(text):
                self.log(f"  Identifiant unique trouvé: '{text}' à l'index {idx}")
                results['identifiant_unique'] = text
                indices_to_remove.append(idx)
                continue
            
            # Numéro CNI
            if not results['numero_cni'] and numero_pattern.match(text):
                self.log(f"  Numéro CNI trouvé: '{text}' à l'index {idx}")
                results['numero_cni'] = text
                indices_to_remove.append(idx)
                continue
            
            # Code poste
            if not results['poste_code'] and poste_pattern.match(text):
                self.log(f"  Code poste trouvé: '{text}' à l'index {idx}")
                results['poste_code'] = text
                indices_to_remove.append(idx)
                continue

        # Assigner les dates (première = délivrance, deuxième = expiration)
        if len(dates_found) >= 1:
            results['date_delivrance'] = dates_found[0][0]
        if len(dates_found) >= 2:
            results['date_expiration'] = dates_found[1][0]

        self.log(f"Champs fixes extraits: {len([v for v in results.values() if v])} sur 5")
        self.log(f"Indices à retirer: {indices_to_remove}")

        results['indices_removed'] = indices_to_remove

        return results

    def detect_anchors(self, data: List[Tuple[str, float, List]]) -> Dict[str, List[Tuple[int, str, float]]]:
        """
        Détecte les ancres avec similarité floue.
        """
        self.log("=== DÉTECTION DES ANCRES ===")

        detected = {field: [] for field in self.anchors}

        for idx, (text, score, _) in enumerate(data):
            text_upper = text.upper()

            for field, anchor_list in self.anchors.items():
                for anchor in anchor_list:
                    sim_score = self.similarity_score(text_upper, anchor)

                    if sim_score >= self.similarity_threshold:
                        self.log(f"  Ancre détectée pour '{field}': '{text}' ~ '{anchor}' (similarité={sim_score:.2f})")
                        detected[field].append((idx, text, sim_score))
                        break

        # Résumé des ancres détectées
        for field, anchors in detected.items():
            if anchors:
                self.log(f"  {field}: {len(anchors)} ancre(s) trouvée(s)")
            else:
                self.log(f"  {field}: aucune ancre trouvée", "WARNING")

        return detected

    def is_likely_label(self, text: str) -> bool:
        """
        Vérifie si un texte ressemble à un label plutôt qu'à une valeur.
        """
        text_upper = text.upper()

        # Vérifier si c'est un format bilingue avec /
        if '/' in text and any(word in text_upper for word in ['PERE', 'FATHER', 'MERE', 'MOTHER', 
                                                                'DATE', 'ADRESSE', 'ADDRESS']):
            self.log(f"    '{text}' identifié comme label (format bilingue avec /)", "DEBUG")
            return True

        # Vérifier la similarité avec tous les labels connus
        for label in self.all_labels:
            sim = self.similarity_score(text_upper, label)
            if sim >= 0.75:
                self.log(f"    '{text}' identifié comme label (similaire à '{label}', score={sim:.2f})", "DEBUG")
                return True

        # Mots-clés spécifiques au verso
        label_words = ['PERE', 'FATHER', 'MERE', 'MOTHER', 'DATE', 'DELIVRANCE', 
                      'ISSUE', 'EXPIRATION', 'EXPIRY', 'ADRESSE', 'ADDRESS',
                      'POSTE', 'IDENTIFICATION', 'POST', 'IDENTIFIANT', 'UNIQUE',
                      'IDENTIFIER', 'AUTORITE', 'AUTHORITY', 'CAMEROUN', 'CAMEROON']

        words = text_upper.split()
        if len(words) > 1:
            matches = sum(1 for word in words if word in label_words)
            if matches >= len(words) / 2:
                self.log(f"    '{text}' identifié comme label (mots clés: {matches}/{len(words)})", "DEBUG")
                return True

        return False

    def extract_by_proximity(self, data: List[Tuple[str, float, List]],
                            anchor_idx: int, field_name: str) -> Optional[str]:
        """
        Extrait la valeur la plus proche d'une ancre.
        """
        self.log(f"  Recherche de valeur pour '{field_name}' près de l'ancre à l'index {anchor_idx}")

        if anchor_idx >= len(data):
            return None

        anchor_text = data[anchor_idx][0]
        anchor_polygon = data[anchor_idx][2]
        anchor_center = self.calculate_center(anchor_polygon)

        candidates = []

        for idx, (text, score, polygon) in enumerate(data):
            if idx == anchor_idx:
                continue

            if self.is_likely_label(text):
                self.log(f"    Ignoré (label): '{text}'", "DEBUG")
                continue

            value_center = self.calculate_center(polygon)

            # Distance
            distance = ((value_center[0] - anchor_center[0])**2 + 
                       (value_center[1] - anchor_center[1])**2) ** 0.5

            # Position relative
            is_right = value_center[0] > anchor_center[0]
            is_below = value_center[1] > anchor_center[1]

            if is_right or is_below:
                proximity_score = 1 / (1 + distance/100)
                candidates.append({
                    'text': text,
                    'score': score * proximity_score,
                    'distance': distance
                })
                self.log(f"    Candidat: '{text}' (distance={distance:.0f}, score={score * proximity_score:.2f})")

        if candidates:
            best = max(candidates, key=lambda x: x['score'])
            self.log(f"  Meilleur candidat pour '{field_name}': '{best['text']}'")
            return best['text']

        return None

    def calculate_center(self, polygon: List[List[int]]) -> Tuple[float, float]:
        """Calcule le centre d'un polygone."""
        x_coords = [p[0] for p in polygon]
        y_coords = [p[1] for p in polygon]
        return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))

    def extract_remaining_fields(self, data: List[Tuple[str, float, List]], 
                                anchors: Dict[str, List[Tuple[int, str, float]]],
                                fixed_fields: Dict) -> Dict:
        """
        Extrait les champs restants (père, mère, adresse, autorité).
        """
        self.log("=== EXTRACTION DES CHAMPS RESTANTS ===")

        results = {
            'pere': None,
            'mere': None,
            'adresse': None,
            'autorite': None,
            'poste_identification': fixed_fields.get('poste_code')  # Déjà extrait
        }

        used_indices = set()
        used_values = set()

        # Extraction par ancres
        for field in ['pere', 'mere', 'adresse', 'autorite']:
            if anchors.get(field, []):
                best_anchor = max(anchors[field], key=lambda x: x[2])
                anchor_idx = best_anchor[0]

                self.log(f"Extraction par ancre pour '{field}':")
                value = self.extract_by_proximity(data, anchor_idx, field)

                if value and not self.is_likely_label(value) and value not in used_values:
                    results[field] = value
                    used_values.add(value)
                    self.log(f"  '{field}' = '{value}' (extrait par ancre)")

        # Pour l'autorité, chercher aussi les noms avec format spécifique
        if not results['autorite']:
            for text, score, _ in data:
                # Pattern pour nom complet (ex: Martin MBARGA NGUELE)
                if score > 0.9 and len(text.split()) >= 2:
                    words = text.split()
                    # Vérifier si c'est un nom propre (mots commençant par majuscule)
                    if all(w[0].isupper() for w in words if w):
                        if text not in used_values and not self.is_likely_label(text):
                            results['autorite'] = text
                            self.log(f"  'autorite' = '{text}' (détection pattern nom)")
                            break

        return results

    def extract(self, ocr_data: Dict) -> Dict[str, any]:
        """
        Méthode principale d'extraction pour le verso.
        """
        self.log("="*50)
        self.log("DÉBUT DE L'EXTRACTION CNI (VERSO)")
        self.log("="*50)

        # 1. Évaluer la qualité
        can_proceed, quality_score = self.assess_quality(ocr_data)

        if not can_proceed:
            return {
                'success': False,
                'quality_score': quality_score,
                'message': 'Qualité OCR insuffisante',
                'data': {}
            }

        # 2. Prétraitement
        texts = ocr_data.get('rec_texts', [])
        scores = ocr_data.get('rec_scores', [])
        polygons = ocr_data.get('rec_polys', [])

        processed_data = self.preprocess(texts, scores, polygons)

        # 3. Extraction des champs à format fixe
        fixed_fields = self.extract_fixed_format_fields(processed_data)

        # Retirer les éléments extraits
        remaining_data = [
            item for idx, item in enumerate(processed_data)
            if idx not in fixed_fields['indices_removed']
        ]

        self.log(f"\nÉléments restants après extraction des champs fixes: {len(remaining_data)}")

        # 4. Détecter les ancres
        anchors = self.detect_anchors(remaining_data)

        # 5. Extraire les champs restants
        remaining_fields = self.extract_remaining_fields(remaining_data, anchors, fixed_fields)

        # 6. Consolider les résultats
        extracted_data = {
            'pere': remaining_fields['pere'],
            'mere': remaining_fields['mere'],
            'date_delivrance': fixed_fields['date_delivrance'],
            'date_expiration': fixed_fields['date_expiration'],
            'adresse': remaining_fields['adresse'],
            'poste_identification': remaining_fields.get('poste_identification') or fixed_fields.get('poste_code'),
            'identifiant_unique': fixed_fields['identifiant_unique'],
            'autorite': remaining_fields['autorite'],
            'numero_cni': fixed_fields.get('numero_cni')
        }

        # Score de confiance
        filled_fields = sum(1 for v in extracted_data.values() if v is not None)
        total_fields = len(extracted_data)
        confidence = filled_fields / total_fields if total_fields > 0 else 0

        self.log("\n=== RÉSULTATS FINAUX ===")
        for field, value in extracted_data.items():
            status = "[SUCCESS]" if value else "[FAILURE]"
            self.log(f"  {status} {field}: {value}")
        self.log(f"Confiance: {confidence:.0%}")

        return {
            'success': True,
            'quality_score': quality_score,
            'confidence': confidence,
            'anchors_detected': {k: len(v) > 0 for k, v in anchors.items()},
            'data': extracted_data
        }


# Exemple d'utilisation
if __name__ == "__main__":
    import json
    
    # Charger les données OCR du verso
    with open('paste-2.txt', 'r') as f:
        ocr_data = json.load(f)
    
    # Créer l'extracteur pour le verso
    extractor = CNIExtractor18B(debug=True)
    
    # Extraire les informations
    result = extractor.extract(ocr_data)
    
    print("\n" + "="*50)
    print("RÉSUMÉ DE L'EXTRACTION (VERSO)")
    print("="*50)
    
    if result['success']:
        print(f"Extraction réussie (confiance: {result['confidence']:.0%})")
        print(f"Qualité OCR: {result['quality_score']:.2f}")
        print("\nDonnées extraites:")
        for field, value in result['data'].items():
            if value:
                print(f"  {field}: {value}")
    else:
        print(f"Extraction échouée: {result['message']}")