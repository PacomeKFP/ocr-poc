import re
from typing import Dict, List, Tuple, Optional
from difflib import SequenceMatcher


class CNIExtractor18F:
    """
    Extracteur de CNI camerounaise utilisant une approche par élimination
    avec détection floue des ancres.
    """

    def __init__(self, quality_threshold: float = 0.5, similarity_threshold: float = 0.70, debug: bool = True):
        """
        Initialise l'extracteur.

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
            'prenom': ['PRENOMS', 'PRENOM', 'GIVEN NAMES', 'GIVEN NAME', 'PRENOMS/GIVEN NAMES'],
            'lieu_naissance': ['LIEU DE NAISSANCE', 'PLACE OF BIRTH',
                               'LIEU DENAISSANCE', 'PLACEOF BIRTH',
                               'LIEU DE NAISSANCE/PLACEOF BIRTH'],
            'profession': ['PROFESSION', 'OCCUPATION', 'PROFESSION/OCCUPATION']
        }

        # Tous les labels possibles (pour filtrage)
        self.all_labels = set()
        for labels in self.anchors.values():
            self.all_labels.update(labels)
        self.all_labels.update(['DATE DE NAISSANCE', 'DATE OF BIRTH',
                                'SEXE', 'SEX', 'TAILLE', 'HEIGHT',
                                'REPUBLIQUE', 'CAMEROUN', 'REPUBLIC', 'CAMEROON',
                                'CARTE', 'NATIONALE', 'IDENTITE', 'IDENTITY', 'CARD',
                                'PROFESSION', 'OCCUPATION', 'SIGNATURE'])

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
        self.log(
            f"Éléments de bonne qualité (>0.7): {good_quality}/{len(scores)}")
        self.log(f"Éléments valides: {len(valid_scores)}")

        # Au moins 8 éléments détectés et score moyen acceptable
        can_proceed = (len(valid_scores) >= 8 and
                       avg_score >= self.quality_threshold and
                       good_quality >= 5)

        self.log(f"Peut continuer: {can_proceed}")

        return can_proceed, avg_score

    def preprocess(self, texts: List[str], scores: List[float],
                   polygons: List) -> List[Tuple[str, float, List]]:
        """
        Prétraite les données OCR en filtrant le bruit.

        Returns:
            Liste de tuples (texte, score, polygone) nettoyés
        """
        self.log("=== PRÉPROCESSING ===")
        processed = []

        for i, (text, score, polygon) in enumerate(zip(texts, scores, polygons)):
            original_text = text

            # Filtrer les scores trop faibles
            if score < 0.3:
                self.log(
                    f"  Filtré (score faible): '{text}' (score={score:.2f})", "DEBUG")
                continue

            # Filtrer les textes vides
            text = text.strip()
            if not text:
                self.log(f"  Filtré (texte vide): index {i}", "DEBUG")
                continue

            # Filtrer les caractères non-latins isolés
            if len(text) <= 2:
                if any(ord(c) > 127 for c in text):
                    self.log(
                        f"  Filtré (caractère non-latin): '{text}'", "DEBUG")
                    continue

            processed.append((text, score, polygon))
            self.log(f"  Gardé: '{text}' (score={score:.2f})")

        self.log(
            f"Éléments après préprocessing: {len(processed)}/{len(texts)}")

        return processed

    def similarity_score(self, str1: str, str2: str) -> float:
        """
        Calcule le score de similarité entre deux chaînes (Jaro-Winkler approximé).
        """
        # Normalisation
        s1 = str1.upper().strip()
        s2 = str2.upper().strip()

        # SequenceMatcher donne un bon compromis
        base_score = SequenceMatcher(None, s1, s2).ratio()

        # Bonus si les premiers caractères correspondent (Jaro-Winkler like)
        prefix_match = 0
        for i in range(min(4, len(s1), len(s2))):
            if s1[i] == s2[i]:
                prefix_match += 1
            else:
                break

        # Ajuster le score avec le bonus de préfixe
        final_score = base_score + (prefix_match * 0.1 * (1 - base_score))

        return min(final_score, 1.0)

    def extract_fixed_format_fields(self, data: List[Tuple[str, float, List]]) -> Dict:
        """
        Extrait les champs à format fixe (date, sexe, taille).

        Returns:
            Dictionnaire avec les champs extraits et les indices à retirer
        """
        self.log("=== EXTRACTION DES CHAMPS À FORMAT FIXE ===")

        results = {
            'date_naissance': None,
            'sexe': None,
            'taille': None
        }
        indices_to_remove = []

        # Patterns de détection
        date_pattern = re.compile(r'^\d{1,2}[./]\d{1,2}[./]\d{4}$')
        taille_pattern = re.compile(r'^[12][,.]?\d{2}$')

        for idx, (text, score, polygon) in enumerate(data):
            # Date de naissance
            if not results['date_naissance'] and date_pattern.match(text):
                self.log(f"  Date trouvée: '{text}' à l'index {idx}")
                results['date_naissance'] = text
                indices_to_remove.append(idx)
                continue

            # Sexe
            if not results['sexe'] and text in ['M', 'F']:
                self.log(f"  Sexe trouvé: '{text}' à l'index {idx}")
                results['sexe'] = text
                indices_to_remove.append(idx)
                continue

            # Taille
            if not results['taille'] and taille_pattern.match(text):
                # Normaliser le format
                taille = text.replace('.', ',')
                if ',' not in taille and len(taille) == 3:
                    taille = taille[0] + ',' + taille[1:]
                self.log(
                    f"  Taille trouvée: '{text}' -> '{taille}' à l'index {idx}")
                results['taille'] = taille
                indices_to_remove.append(idx)
                continue

        self.log(
            f"Champs fixes extraits: Date={results['date_naissance']}, Sexe={results['sexe']}, Taille={results['taille']}")
        self.log(f"Indices à retirer: {indices_to_remove}")

        # Retirer les éléments extraits de la liste
        results['indices_removed'] = indices_to_remove

        return results

    def detect_anchors(self, data: List[Tuple[str, float, List]]) -> Dict[str, List[Tuple[int, str, float]]]:
        """
        Détecte les ancres avec similarité floue.

        Returns:
            Dictionnaire {type_champ: [(indice, texte_trouvé, score_similarité)]}
        """
        self.log("=== DÉTECTION DES ANCRES ===")

        detected = {field: [] for field in self.anchors}

        for idx, (text, score, _) in enumerate(data):
            text_upper = text.upper()

            # Vérifier contre chaque type d'ancre
            for field, anchor_list in self.anchors.items():
                for anchor in anchor_list:
                    sim_score = self.similarity_score(text_upper, anchor)

                    if sim_score >= self.similarity_threshold:
                        self.log(
                            f"  Ancre détectée pour '{field}': '{text}' ~ '{anchor}' (similarité={sim_score:.2f})")
                        detected[field].append((idx, text, sim_score))
                        break
                    elif sim_score > 0.7:  # Log les correspondances proches
                        self.log(
                            f"    Correspondance proche pour '{field}': '{text}' ~ '{anchor}' (similarité={sim_score:.2f})", "DEBUG")

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

        # Vérifier si le texte contient un slash (caractéristique des labels bilingues)
        if '/' in text and any(word in text_upper for word in ['NOM', 'SURNAME', 'PRENOM', 'GIVEN', 'DATE', 'LIEU', 'PLACE', 'SEXE', 'SEX', 'TAILLE', 'HEIGHT']):
            self.log(
                f"    '{text}' identifié comme label (format bilingue avec /)", "DEBUG")
            return True

        # Vérifier la similarité avec tous les labels connus
        for label in self.all_labels:
            sim = self.similarity_score(text_upper, label)
            if sim >= 0.75:
                self.log(
                    f"    '{text}' identifié comme label (similaire à '{label}', score={sim:.2f})", "DEBUG")
                return True

        # Vérifier les patterns de labels composés
        label_words = ['CARTE', 'NATIONALE', 'REPUBLIQUE', 'DATE', 'LIEU',
                       'PLACE', 'BIRTH', 'NAISSANCE', 'IDENTITY', 'CARD',
                       'REPUBLIC', 'CAMEROON', 'CAMEROUN', 'OF', 'DE', 'DU',
                       'PRENOMS', 'PRENOM', 'GIVEN', 'NAMES', 'NAME', 'NOM', 'SURNAME']

        words = text_upper.split()
        if len(words) > 1:
            matches = sum(1 for word in words if word in label_words)
            if matches >= len(words) / 2:
                self.log(
                    f"    '{text}' identifié comme label (mots clés: {matches}/{len(words)})", "DEBUG")
                return True

        # Vérifier si c'est exactement un mot clé
        if text_upper in label_words:
            self.log(
                f"    '{text}' identifié comme label (mot clé exact)", "DEBUG")
            return True

        return False

    def extract_by_proximity(self, data: List[Tuple[str, float, List]],
                             anchor_idx: int, field_name: str) -> Optional[str]:
        """
        Extrait la valeur la plus proche d'une ancre.
        """
        self.log(
            f"  Recherche de valeur pour '{field_name}' près de l'ancre à l'index {anchor_idx}")

        if anchor_idx >= len(data):
            return None

        anchor_text = data[anchor_idx][0]
        anchor_polygon = data[anchor_idx][2]
        anchor_center = self.calculate_center(anchor_polygon)

        self.log(f"    Ancre: '{anchor_text}' au centre {anchor_center}")

        candidates = []

        for idx, (text, score, polygon) in enumerate(data):
            if idx == anchor_idx:
                continue

            # Ignorer les labels
            if self.is_likely_label(text):
                self.log(f"    Ignoré (label): '{text}'", "DEBUG")
                continue

            value_center = self.calculate_center(polygon)

            # Calculer la distance
            distance = ((value_center[0] - anchor_center[0])**2 +
                        (value_center[1] - anchor_center[1])**2) ** 0.5

            # Vérifier la position relative (à droite ou en dessous)
            is_right = value_center[0] > anchor_center[0]
            is_below = value_center[1] > anchor_center[1]

            if is_right or is_below:
                # Prioriser les éléments proches
                proximity_score = 1 / (1 + distance/100)
                candidates.append({
                    'text': text,
                    'score': score * proximity_score,
                    'distance': distance,
                    'position': 'droite' if is_right else 'dessous'
                })
                self.log(
                    f"    Candidat: '{text}' ({candidates[-1]['position']}, distance={distance:.0f}, score={candidates[-1]['score']:.2f})")

        if candidates:
            # Prendre le meilleur candidat
            best = max(candidates, key=lambda x: x['score'])
            self.log(
                f"  Meilleur candidat pour '{field_name}': '{best['text']}'")
            return best['text']

        self.log(f"  Aucun candidat trouvé pour '{field_name}'", "WARNING")
        return None

    def calculate_center(self, polygon: List[List[int]]) -> Tuple[float, float]:
        """Calcule le centre d'un polygone."""
        x_coords = [p[0] for p in polygon]
        y_coords = [p[1] for p in polygon]
        return (sum(x_coords) / len(x_coords), sum(y_coords) / len(y_coords))

    def extract_remaining_fields(self, data: List[Tuple[str, float, List]],
                                 anchors: Dict[str, List[Tuple[int, str, float]]]) -> Dict:
        """
        Extrait nom, prénom et lieu de naissance.
        """
        self.log("=== EXTRACTION DES CHAMPS RESTANTS ===")

        results = {
            'nom': None,
            'prenom': None,
            'lieu_naissance': None,
            'profession': None,
        }

        used_indices = set()
        used_values = set()  # Pour éviter les doublons

        # Si on a des ancres, les utiliser
        for field in ['nom', 'prenom', 'lieu_naissance', 'profession']:
            if anchors[field]:
                # Prendre l'ancre avec le meilleur score de similarité
                best_anchor = max(anchors[field], key=lambda x: x[2])
                anchor_idx = best_anchor[0]

                self.log(f"Extraction par ancre pour '{field}':")
                value = self.extract_by_proximity(data, anchor_idx, field)

                if value and not self.is_likely_label(value) and value not in used_values:
                    results[field] = value
                    used_values.add(value)
                    # Marquer l'indice comme utilisé
                    for idx, (text, _, _) in enumerate(data):
                        if text == value:
                            used_indices.add(idx)
                            self.log(
                                f"  '{field}' = '{value}' (extrait par ancre)")
                            break
                else:
                    self.log(
                        f"  Échec de l'extraction par ancre pour '{field}'", "WARNING")

        # Pour les champs manquants, utiliser l'analyse positionnelle
        self.log("Extraction positionnelle pour les champs manquants:")

        remaining_texts = []
        for idx, (text, score, polygon) in enumerate(data):
            if idx not in used_indices and not self.is_likely_label(text) and text not in used_values:
                y_pos = self.calculate_center(polygon)[1]
                remaining_texts.append({
                    'text': text,
                    'score': score,
                    'y_position': y_pos,
                    'index': idx
                })
                self.log(
                    f"  Texte restant: '{text}' (y={y_pos:.0f}, score={score:.2f})")

        # Trier par position verticale
        remaining_texts.sort(key=lambda x: x['y_position'])

        # Assigner les champs manquants par position
        if not results['nom'] and remaining_texts:
            results['nom'] = remaining_texts[0]['text']
            used_values.add(remaining_texts[0]['text'])
            self.log(
                f"  'nom' = '{results['nom']}' (position: premier élément)")
            remaining_texts.pop(0)

        if not results['prenom'] and remaining_texts:
            results['prenom'] = remaining_texts[0]['text']
            used_values.add(remaining_texts[0]['text'])
            self.log(
                f"  'prenom' = '{results['prenom']}' (position: deuxième élément)")
            remaining_texts.pop(0)

        if not results['lieu_naissance'] and remaining_texts:
            # Le lieu est souvent après le nom/prénom
            results['lieu_naissance'] = remaining_texts[0]['text']
            self.log(
                f"  'lieu_naissance' = '{results['lieu_naissance']}' (position: troisième élément)")

        return results

    def extract(self, ocr_data: Dict) -> Dict[str, any]:
        """
        Méthode principale d'extraction.

        Returns:
            Dictionnaire avec les champs extraits et les métadonnées
        """
        self.log("="*50)
        self.log("DÉBUT DE L'EXTRACTION CNI")
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

        self.log(
            f"\nÉléments restants après extraction des champs fixes: {len(remaining_data)}")
        for text, score, _ in remaining_data:
            self.log(f"  - '{text}' (score={score:.2f})")

        # 4. Détecter les ancres
        anchors = self.detect_anchors(remaining_data)

        # 5. Extraire les champs restants
        remaining_fields = self.extract_remaining_fields(
            remaining_data, anchors)

        # 6. Consolider les résultats
        extracted_data = {
            'nom': remaining_fields['nom'],
            'prenom': remaining_fields['prenom'],
            'date_naissance': fixed_fields['date_naissance'],
            'lieu_naissance': remaining_fields['lieu_naissance'],
            'sexe': fixed_fields['sexe'],
            'taille': fixed_fields['taille'],
            'profession': remaining_fields['profession']
        }

        # Calculer le score de confiance
        filled_fields = sum(
            1 for v in extracted_data.values() if v is not None)
        confidence = filled_fields / 6.0

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
