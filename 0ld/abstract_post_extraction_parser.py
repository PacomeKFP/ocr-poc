import re
from typing import Dict, List, Any
import logging
from card_side import CardSide
from field_rule import FieldRule
from abc import ABC, abstractmethod

class AbstractPostExtractionParser(ABC):
    """
    Extracteur CNI simplifié basé sur l'ordre séquentiel et la validation par patterns
    
    Principe:
    1. Supprime tous les éléments qui ressemblent aux USELESS_ITEMS et BOUNDS
    2. Dans ce qui reste, prend les éléments dans l'ordre attendu
    3. Valide chaque élément avec des règles spécifiques
    4. Procède par élimination et correction
    """
    
    def __init__(self, debug: bool = True):
        self.debug = debug
        self.logger = logging.getLogger(__name__)
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        
        # Configuration des éléments à supprimer
        self.setup_removal_patterns()
        
        # Configuration des règles de validation
        self.setup_field_rules()
    
    def setup_removal_patterns(self):
        """Configure les patterns d'éléments à supprimer"""
        
        # Éléments inutiles à supprimer (avec variations d'erreurs OCR)
        self.useless_patterns = [
            # Headers/Titres
            r".*REPUBLIQUE.*CAMEROUN.*",
            r".*NATIONAL.*IDENITY.*CARD.*",
            r".*REPUBLIC.*CAMEROON.*",
            r".*CARTE.*NATIONALE.*IDENTITE.*",
            
            # Labels/Étiquettes (à supprimer car on ne veut que les valeurs)
            r".*NOM.*SURNAME.*",
            r".*PRENOMS.*GIVEN.*NAMES.*",
            r".*DATE.*NAISSANCE.*BIRTH.*",
            r".*LIEU.*NAISSANCE.*PLACE.*BIRTH.*",
            r".*SEXE.*SEX.*",
            r".*TAILLE.*HEIGHT.*",
            r".*PROFESSION.*OCCUPATION.*",
            r".*SIGNATURE.*",
            
            # Verso - Labels
            r".*PERE.*FATHER.*",
            r".*MERE.*MOTHER.*",
            r".*S\.P\..*S\.M\..*",
            r".*AUTORITE.*AUTHORITY.*",
            r".*DATE.*DELIVRANCE.*",
            r".*DATE.*ISSUE.*",
            r".*DATE.*EXPIRATION.*",
            r".*DATE.*EXPIRY.*",
            r".*IDENTIFIANT.*UNIQUE.*",
            r".*UNIQUE.*IDENTIFIER.*",
            r".*ADRESSE.*ADDRESS.*",
            r".*POSTE.*IDENTIFICATION.*",
            r".*IDENTIFICATION.*POS.*",
            # Éléments techniques/parasites
            r".*CAM.*UN.*",  # Caractères déformés
            r".*CAMERO.*",
            r"^[A-Z]$",  # Lettres isolées (sauf M/F pour le sexe)
            r"^\d{1,2}$",  # Chiffres isolés courts
            r".*URIOURIDENTIFIER.*",  # Erreur OCR connue
        ]
        
        # Compile les patterns
        self.compiled_useless_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.useless_patterns
        ]
    
    @abstractmethod
    def setup_field_rules(self):
        """Configure les règles de validation pour chaque champ"""
        
        # Ordre attendu des champs pour le RECTO
        self.recto_field_rules = [
            FieldRule(
                name="NOM",
                pattern=r"^[A-Z\s]{2,}$",
                description="Nom de famille en majuscules",
                validator_func=self.validate_name,
                expected_position=0
            ),
            FieldRule(
                name="PRENOMS", 
                pattern=r"^[A-Z\s]{2,}$",
                description="Prénoms en majuscules",
                validator_func=self.validate_name,
                expected_position=1
            ),
            FieldRule(
                name="DATE_NAISSANCE",
                pattern=r"^\d{2}\.\d{2}\.\d{4}$",
                description="Date format DD.MM.YYYY",
                validator_func=self.validate_date,
                expected_position=2
            ),
            FieldRule(
                name="LIEU_NAISSANCE",
                pattern=r"^[A-Z\s]{2,}$", 
                description="Lieu de naissance en majuscules",
                validator_func=self.validate_place,
                expected_position=3
            ),
            FieldRule(
                name="SEXE",
                pattern=r"^[MF]$",
                description="M ou F uniquement",
                validator_func=self.validate_gender,
                expected_position=4
            ),
            FieldRule(
                name="TAILLE",
                pattern=r"^\d,\d{2}$",
                description="Taille format X,XX",
                validator_func=self.validate_height,
                expected_position=5
            ),
            FieldRule(
                name="PROFESSION",
                pattern=r"^[A-Z\s]{2,}$",
                description="Profession en majuscules",
                validator_func=self.validate_profession,
                expected_position=6
            )
        ]
        
        # Ordre attendu des champs pour le VERSO  
        self.verso_field_rules = [
            FieldRule(
                name="PERE",
                pattern=r"^[A-Z\s]{3,}$",
                description="Nom du père",
                validator_func=self.validate_name,
                expected_position=0
            ),
            FieldRule(
                name="MERE",
                pattern=r"^[A-Z\s]{3,}$", 
                description="Nom de la mère",
                validator_func=self.validate_name,
                expected_position=1
            ),
            FieldRule(
                name="SP_SM",
                pattern=r"^\d{4,}$",
                description="Code numérique S.P./S.M.",
                validator_func=self.validate_numeric_code,
                expected_position=2
            ),
            FieldRule(
                name="POSTE_IDENTIFICATION",
                pattern=r"^[A-Z0-9]{2,10}$",
                description="Code du poste d'identification",
                validator_func=self.validate_identification_post,
                expected_position=3
            ),
            FieldRule(
                name="DATE_DELIVRANCE",
                pattern=r"^\d{2}\.\d{2}\.\d{4}$",
                description="Date de délivrance",
                validator_func=self.validate_date,
                expected_position=4
            ),
            FieldRule(
                name="ADRESSE",
                pattern=r"^[A-Z\s]{2,}$",
                description="Adresse/Ville",
                validator_func=self.validate_place,
                expected_position=5
            ),
            FieldRule(
                name="DATE_EXPIRATION", 
                pattern=r"^\d{2}\.\d{2}\.\d{4}$",
                description="Date d'expiration",
                validator_func=self.validate_date,
                expected_position=6
            ),
            FieldRule(
                name="IDENTIFIANT_UNIQUE",
                pattern=r"^\d{15,}$",
                description="Identifiant unique long",
                validator_func=self.validate_unique_id,
                expected_position=7
            ),
            # FieldRule(
            #     name="AUTORITE",
            #     pattern=r"^[A-Z\s]{5,}$",
            #     description="Nom de l'autorité signataire",
            #     validator_func=self.validate_authority,
            #     expected_position=8
            # )
        ]
    
    # Fonctions de validation spécifiques
    def validate_name(self, text: str) -> bool:
        """Valide un nom (pas de chiffres, au moins 2 caractères)"""
        return bool(re.match(r"^[A-Z\s]{2,}$", text)) and not any(char.isdigit() for char in text)
    
    def validate_date(self, text: str) -> bool:
        """Valide une date DD.MM.YYYY"""
        if not re.match(r"^\d{2}\.\d{2}\.\d{4}$", text):
            return False
        
        try:
            day, month, year = map(int, text.split('.'))
            return 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2040
        except:
            return False
    
    def validate_place(self, text: str) -> bool:
        """Valide un lieu (ville, pays, etc.)"""
        return self.validate_name(text) and len(text) >= 3
    
    def validate_gender(self, text: str) -> bool:
        """Valide le sexe (M ou F uniquement)"""
        return text.strip().upper() in ['M', 'F']
    
    def validate_height(self, text: str) -> bool:
        """Valide la taille (format X,XX)"""
        if not re.match(r"^\d,\d{2}$", text):
            return False
        
        try:
            height = float(text.replace(',', '.'))
            return 0.5 <= height <= 2.5  # Tailles humaines réalistes
        except:
            return False
    
    def validate_profession(self, text: str) -> bool:
        """Valide une profession"""
        return self.validate_name(text) and len(text) >= 3
    
    def validate_numeric_code(self, text: str) -> bool:
        """Valide un code numérique"""
        return text.isdigit() and len(text) >= 4
    
    def validate_identification_post(self, text: str) -> bool:
        """Valide un code de poste d'identification (alphanumerique court)"""
        return bool(re.match(r"^[A-Z0-9]{2,10}$", text)) and len(text) <= 10
    
    def validate_unique_id(self, text: str) -> bool:
        """Valide l'identifiant unique (17 chiffres typiquement)"""
        return text.isdigit() and len(text) >= 15
    
    def validate_authority(self, text: str) -> bool:
        """Valide le nom d'une autorité"""
        return self.validate_name(text) and len(text) >= 5
    
    def log(self, message: str):
        """Log de débogage"""
        if self.debug:
            print(f"[DEBUG] {message}")
    
    def remove_useless_elements(self, texts: List[str]) -> List[str]:
        """
        Supprime tous les éléments qui correspondent aux patterns inutiles
        """
        filtered_texts = []
        
        for text in texts:
            text = text.strip()
            if not text:
                continue
            
            # Vérifie si le texte correspond à un pattern inutile
            is_useless = False
            for pattern in self.compiled_useless_patterns:
                if pattern.match(text):
                    is_useless = True
                    self.log(f"Removed useless: '{text}'")
                    break
            
            if not is_useless:
                filtered_texts.append(text)
                self.log(f"Kept: '{text}'")
        
        return filtered_texts
    
    def extract_by_sequential_validation(self, 
                                       filtered_texts: List[str], 
                                       field_rules: List[FieldRule]) -> Dict[str, Any]:
        """
        Extrait les champs en utilisant l'ordre séquentiel et la validation
        """
        results = {}
        used_indices = set()
        
        self.log(f"Starting sequential extraction with {len(filtered_texts)} texts")
        self.log(f"Texts to process: {filtered_texts}")
        
        # Pour chaque règle de champ, dans l'ordre
        for rule in field_rules:
            self.log(f"\nProcessing field: {rule.name}")
            
            best_match = None
            best_score = 0
            best_index = -1
            
            # Cherche parmi les textes non utilisés
            for i, text in enumerate(filtered_texts):
                if i in used_indices:
                    continue
                
                # Vérifie si le texte correspond à la règle
                if re.match(rule.pattern, text):
                    # Validation supplémentaire avec la fonction spécifique
                    if rule.validator_func and rule.validator_func(text):
                        # Score basé sur la position (plus c'est proche de l'attendu, mieux c'est)
                        position_score = 1.0
                        if rule.expected_position is not None:
                            distance = abs(i - rule.expected_position)
                            position_score = max(0.1, 1.0 - (distance * 0.2))
                        
                        if position_score > best_score:
                            best_match = text
                            best_score = position_score
                            best_index = i
                            
                        self.log(f"  Candidate '{text}' at index {i}, score: {position_score:.3f}")
            
            if best_match:
                results[rule.name] = {
                    "value": best_match,
                    "confidence": best_score,
                    "index": best_index,
                    "rule": rule.description
                }
                used_indices.add(best_index)
                self.log(f"  ✓ Selected '{best_match}' for {rule.name}")
            else:
                self.log(f"  ✗ No valid match found for {rule.name}")
        
        return results
    
    def extract_with_fallback_strategies(self, 
                                       filtered_texts: List[str], 
                                       field_rules: List[FieldRule]) -> Dict[str, Any]:
        """
        Extraction avec stratégies de fallback pour les champs non trouvés
        """
        results = self.extract_by_sequential_validation(filtered_texts, field_rules)
        
        # Stratégie de fallback : patterns globaux
        missing_fields = [rule for rule in field_rules if rule.name not in results]
        
        if missing_fields:
            self.log(f"\nApplying fallback strategies for {len(missing_fields)} missing fields")
            
            used_values = set(r["value"] for r in results.values())
            
            for rule in missing_fields:
                self.log(f"Fallback for {rule.name}")
                
                # Cherche parmi tous les textes non utilisés
                for text in filtered_texts:
                    if text in used_values:
                        continue
                    
                    # Validation moins stricte (pattern seulement)
                    if re.match(rule.pattern, text):
                        results[rule.name] = {
                            "value": text,
                            "confidence": 0.5,  # Confiance réduite pour fallback
                            "index": -1,
                            "rule": f"FALLBACK: {rule.description}"
                        }
                        used_values.add(text)
                        self.log(f"  ✓ Fallback match '{text}' for {rule.name}")
                        break
        
        return results
    
    def post_process_results(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Post-traitement pour corriger les erreurs communes
        """
        processed = {}
        
        for field_name, field_data in results.items():
            value = field_data["value"]
            
            # Corrections spécifiques par type de champ
            if "DATE" in field_name:
                # Assure le format de date correct
                value = self.normalize_date(value)
            
            elif field_name in ["NOM", "PRENOMS", "PERE", "MERE", "AUTORITE"]:
                # Normalise les noms
                value = value.upper().strip()
            
            elif field_name == "SEXE":
                # Normalise le sexe
                value = value.upper().strip()
            
            elif field_name == "TAILLE":
                # Normalise la taille
                value = self.normalize_height(value)
            
            processed[field_name] = {
                **field_data,
                "normalized_value": value
            }
        
        return processed
    
    def normalize_date(self, date_str: str) -> str:
        """Normalise le format de date"""
        match = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", date_str)
        if match:
            day, month, year = match.groups()
            return f"{day.zfill(2)}.{month.zfill(2)}.{year}"
        return date_str
    
    def normalize_height(self, height_str: str) -> str:
        """Normalise le format de taille"""
        # Assure le format X,XX
        if '.' in height_str:
            height_str = height_str.replace('.', ',')
        return height_str

    def parse(self, ocr_data: Dict, side: CardSide = CardSide.RECTO) -> Dict[str, Any]:
        """
        Méthode principale d'extraction
        
        Args:
            ocr_data: Données OCR au format JSON
            side: "recto" ou "verso"
        
        Returns:
            Dictionnaire avec les champs extraits
        """
        self.log(f"=== DÉBUT EXTRACTION ALGORITHMIQUE - {side} ===")

        # 1. Récupère les textes
        texts = ocr_data.get("rec_texts", [])
        self.log(f"Input texts: {texts}")
        
        # 2. Supprime les éléments inutiles
        filtered_texts = self.remove_useless_elements(texts)
        self.log(f"Filtered texts: {filtered_texts}")
        
        # 3. Sélectionne les règles selon le côté
        field_rules = self.recto_field_rules if side == CardSide.RECTO else self.verso_field_rules

        # 4. Extraction séquentielle avec validation
        results = self.extract_with_fallback_strategies(filtered_texts, field_rules)
        
        # 5. Post-traitement
        final_results = self.post_process_results(results)
        
        # 6. Génère un rapport
        report = self.generate_extraction_report(final_results, field_rules)

        self.log(f"=== EXTRACTION TERMINÉE - {side} ===")

        return {
            "extracted_fields": final_results,
            "extraction_report": report,
            "filtered_texts": filtered_texts,
            "original_texts": texts
        }
    
    def generate_extraction_report(self, results: Dict, field_rules: List[FieldRule]) -> Dict[str, Any]:
        """Génère un rapport d'extraction"""
        
        total_fields = len(field_rules)
        extracted_fields = len(results)
        
        avg_confidence = sum(r["confidence"] for r in results.values()) / len(results) if results else 0
        
        return {
            "extraction_rate": extracted_fields / total_fields,
            "total_expected": total_fields,
            "total_extracted": extracted_fields,
            "average_confidence": avg_confidence,
            "missing_fields": [rule.name for rule in field_rules if rule.name not in results],
            "extracted_fields": list(results.keys())
        }