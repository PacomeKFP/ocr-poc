import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher


class CNIExtractor25B:
    """
    Extracteur pour le nouveau format de CNI camerounaise (2025) 
    utilisant une approche par élimination avec détection floue des ancres.
    """

    def __init__(self, quality_threshold: float = 0.5, similarity_threshold: float = 0.70, debug: bool = True):
        """
        Initialise l'extracteur pour le nouveau format.

        Args:
            quality_threshold: Seuil minimal de qualité OCR pour procéder
            similarity_threshold: Seuil de similarité pour la détection des ancres
            debug: Active les logs de débogage
        """
        self.quality_threshold = quality_threshold
        self.similarity_threshold = similarity_threshold
        self.debug = debug

        # Ancres possibles pour chaque champ
        self.anchors = {
            'nom': ['NOM', 'SURNAME', 'NOM/SURNAME'],
            'prenom': ['PRENOMS', 'PRENOM', 'GIVEN NAMES', 'GIVEN NAME', 
                      'PRENOMS/GIVEN NAMES', 'PRENOMS/GIVEN NAME'],
            'date_naissance': ['DATE DE NAISSANCE', 'DATE OF BIRTH', 
                             'DATE DENAISSANCE', 'DATEOF BIRTH',
                             'DATE DE NAISSANCE/DATE OF BIRTH'],
            'date_expiration': ['DATE D\'EXPIRATION', 'DATE OF EXPIRY',
                              'DATED\'EXPIRATION', 'DATEOF EXPIRY',
                              'DATE D\'EXPIRATION/DATE OF EXPIRY'],
            'sexe': ['SEXE', 'SEX', 'SEXE/SEX'],
            'signature': ['SIGNATURE', 'HOLDER\'S SIGNATURE', 
                         'SIGNATURE/HOLDER\'S SIGNATURE']
        }

        # Labels à ignorer (filigranes et textes de fond)
        self.ignore_words = {
            'TRAVAIL', 'PATRIE', 'WORK', 'FATHERLAND', 
            'CMR', 'CAMEROUN', 'CAMEROON',
            'REPUBLIQUE', 'REPUBLIC', 'DU', 'OF',
            'CARTE', 'NATIONALE', 'IDENTITE', 
            'NATIONAL', 'IDENTITY', 'CARD'
        }

        # Tous les labels possibles (pour filtrage)
        self.all_labels = set()
        for labels in self.anchors.values():
            self.all_labels.update(labels)
        self.all_labels.update(self.ignore_words)
        self.all_labels.update(['SIGNATURE', 'HOLDER\'S'])

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

        # Au moins 6 éléments détectés pour le nouveau format
        can_proceed = (len(valid_scores) >= 6 and 
                      avg_score >= self.quality_threshold and
                      good_quality >= 4)

        self.log(f"Peut continuer: {can_proceed}")

        return can_proceed, avg_score

    def preprocess(self, texts: List[str], scores: List[float],
                  polygons: List) -> List[Tuple[str, float, List]]:
        """
        Prétraite les données OCR en filtrant le bruit et les filigranes.
        """
        self.log("=== PRÉPROCESSING ===")
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

            # Filtrer les caractères non-latins isolés (国, etc.)
            if len(text) <= 2:
                if any(ord(c) > 127 for c in text):
                    self.log(f"  Filtré (caractère non-latin): '{text}'", "DEBUG")
                    continue

            # Filtrer les mots isolés qui sont des filigranes connus
            if text.upper() in self.ignore_words:
                self.log(f"  Filtré (filigrane): '{text}'", "DEBUG")
                continue

            # Filtrer CMR et codes pays de 3 lettres
            if len(text) == 3 and text.isupper() and text.isalpha():
                self.log(f"  Filtré (code pays probable): '{text}'", "DEBUG")
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
        Extrait les champs à format fixe (numéro, dates, sexe).
        """
        self.log("=== EXTRACTION DES CHAMPS À FORMAT FIXE ===")

        results = {
            'numero_carte': None,
            'date_naissance': None,
            'date_expiration': None,
            'sexe': None
        }
        indices_to_remove = []

        # Patterns de détection
        date_pattern = re.compile(r'^\d{1,2}\.\d{1,2}\.\d{4}$')  # Format avec points
        numero_pattern = re.compile(r'^\d{9}$')  # Numéro de carte (9 chiffres)

        dates_found = []
        
        for idx, (text, score, polygon) in enumerate(data):
            # Numéro de carte (9 chiffres)
            if not results['numero_carte'] and numero_pattern.match(text):
                self.log(f"  Numéro de carte trouvé: '{text}' à l'index {idx}")
                results['numero_carte'] = text
                indices_to_remove.append(idx)
                continue
            
            # Dates (format avec points)
            if date_pattern.match(text):
                dates_found.append((text, idx, polygon))
                self.log(f"  Date trouvée: '{text}' à l'index {idx}")
                indices_to_remove.append(idx)
                continue
            
            # Sexe
            if not results['sexe'] and text in ['M', 'F']:
                self.log(f"  Sexe trouvé: '{text}' à l'index {idx}")
                results['sexe'] = text
                indices_to_remove.append(idx)
                continue

        # Distinguer les dates par leur année
        for date_text, idx, polygon in dates_found:
            year = int(date_text.split('.')[-1])
            
            # Date de naissance : année < 2010 généralement
            if not results['date_naissance'] and year < 2010:
                results['date_naissance'] = date_text
                self.log(f"  Date de naissance identifiée: {date_text} (année {year})")
            
            # Date d'expiration : année > 2020 généralement
            elif not results['date_expiration'] and year > 2020:
                results['date_expiration'] = date_text
                self.log(f"  Date d'expiration identifiée: {date_text} (année {year})")

        # Si on n'a pas pu distinguer par l'année, prendre par ordre
        if not results['date_naissance'] and dates_found:
            results['date_naissance'] = dates_found[0][0]
        if not results['date_expiration'] and len(dates_found) > 1:
            results['date_expiration'] = dates_found[1][0]

        self.log(f"Champs fixes extraits: {len([v for v in results.values() if v])} sur 4")
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

        # Vérifier si c'est un mot isolé de filigrane
        if text_upper in self.ignore_words:
            self.log(f"    '{text}' identifié comme filigrane", "DEBUG")
            return True

        # Vérifier si c'est un format bilingue avec /
        if '/' in text and any(word in text_upper for word in ['NOM', 'SURNAME', 'PRENOM', 'GIVEN', 
                                                                'DATE', 'SEXE', 'SEX', 'SIGNATURE']):
            self.log(f"    '{text}' identifié comme label (format bilingue avec /)", "DEBUG")
            return True

        # Vérifier la similarité avec tous les labels connus
        for label in self.all_labels:
            sim = self.similarity_score(text_upper, label)
            if sim >= 0.75:
                self.log(f"    '{text}' identifié comme label (similaire à '{label}', score={sim:.2f})", "DEBUG")
                return True

        # Mots-clés spécifiques
        label_words = ['NOM', 'SURNAME', 'PRENOMS', 'PRENOM', 'GIVEN', 'NAMES', 'NAME',
                      'DATE', 'NAISSANCE', 'BIRTH', 'EXPIRATION', 'EXPIRY',
                      'SEXE', 'SEX', 'SIGNATURE', 'HOLDER\'S']

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
                                anchors: Dict[str, List[Tuple[int, str, float]]]) -> Dict:
        """
        Extrait les champs restants (nom, prénom).
        """
        self.log("=== EXTRACTION DES CHAMPS RESTANTS ===")

        results = {
            'nom': None,
            'prenom': None
        }

        used_values = set()

        # Extraction par ancres
        for field in ['nom', 'prenom']:
            if anchors.get(field, []):
                best_anchor = max(anchors[field], key=lambda x: x[2])
                anchor_idx = best_anchor[0]

                self.log(f"Extraction par ancre pour '{field}':")
                value = self.extract_by_proximity(data, anchor_idx, field)

                if value and not self.is_likely_label(value) and value not in used_values:
                    results[field] = value
                    used_values.add(value)
                    self.log(f"  '{field}' = '{value}' (extrait par ancre)")

        # Si les champs manquent, chercher les textes restants valides
        if not results['nom'] or not results['prenom']:
            remaining_texts = []
            for text, score, polygon in data:
                # Vérifier que c'est un nom valide (alphabétique, score élevé)
                if (text not in used_values and 
                    not self.is_likely_label(text) and
                    score > 0.9 and
                    text.isalpha() and
                    len(text) > 2):
                    
                    y_pos = self.calculate_center(polygon)[1]
                    remaining_texts.append({
                        'text': text,
                        'score': score,
                        'y_position': y_pos
                    })
                    self.log(f"  Texte candidat nom/prénom: '{text}' (y={y_pos:.0f}, score={score:.2f})")

            # Trier par position verticale
            remaining_texts.sort(key=lambda x: x['y_position'])

            # Assigner les champs manquants
            if not results['nom'] and remaining_texts:
                results['nom'] = remaining_texts[0]['text']
                self.log(f"  'nom' = '{results['nom']}' (position: premier élément)")
                remaining_texts.pop(0)

            if not results['prenom'] and remaining_texts:
                results['prenom'] = remaining_texts[0]['text']
                self.log(f"  'prenom' = '{results['prenom']}' (position: deuxième élément)")

        return results

    def extract(self, ocr_data: Dict) -> Dict[str, any]:
        """
        Méthode principale d'extraction pour le nouveau format.
        """
        self.log("="*50)
        self.log("DÉBUT DE L'EXTRACTION CNI (FORMAT 2025)")
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
        for text, score, _ in remaining_data:
            self.log(f"  - '{text}' (score={score:.2f})")

        # 4. Détecter les ancres
        anchors = self.detect_anchors(remaining_data)

        # 5. Extraire les champs restants
        remaining_fields = self.extract_remaining_fields(remaining_data, anchors)

        # 6. Consolider les résultats (gardant les mêmes clés pour la cohérence)
        extracted_data = {
            'numero_carte': fixed_fields['numero_carte'],
            'nom': remaining_fields['nom'],
            'prenom': remaining_fields['prenom'],
            'date_naissance': fixed_fields['date_naissance'],
            'date_expiration': fixed_fields['date_expiration'],
            'sexe': fixed_fields['sexe']
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
    
    # Charger les données OCR du nouveau format
    with open('paste.txt', 'r') as f:
        ocr_data = json.load(f)
    
    # Créer l'extracteur pour le nouveau format
    extractor = CNIExtractor2025F(debug=True)
    
    # Extraire les informations
    result = extractor.extract(ocr_data)
    
    print("\n" + "="*50)
    print("RÉSUMÉ DE L'EXTRACTION (FORMAT 2025)")
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