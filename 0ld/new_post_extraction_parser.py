import re
from typing import Dict, List, Any
import logging
from field_rule import FieldRule
from abstract_post_extraction_parser import AbstractPostExtractionParser

class NewPostExtractionParser(AbstractPostExtractionParser):
    """
    Extracteur CNI simplifié basé sur l'ordre séquentiel et la validation par patterns
    
    Principe:
    1. Supprime tous les éléments qui ressemblent aux USELESS_ITEMS et BOUNDS
    2. Dans ce qui reste, prend les éléments dans l'ordre attendu
    3. Valide chaque élément avec des règles spécifiques
    4. Procède par élimination et correction
    """
    
    def __init__(self, debug: bool = True):
        super().__init__(debug)
        
    
    def setup_removal_patterns(self):
        """Configure les patterns d'éléments à supprimer"""
        
        # Éléments inutiles à supprimer (avec variations d'erreurs OCR)
        self.useless_patterns = [
            # Headers/Titres
            r".*REPUBLIQUE.*CAMEROUN.*",
            r".*NATIONAL.*IDENTITY.*CARD.*",
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
    
    