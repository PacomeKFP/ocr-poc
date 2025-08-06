import torch
from ocr.llm_post_processor import LLMPostProcessor
from ocr.llm_post_processor_lora import LLMPostProcessorLoRA
from ocr.card_side import CardSide
from ocr.card_version import CardVersion
from ocr.paddle_extractor import PaddleExtractor
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IDCardDataExtractor:
    def __init__(self, llm_model_path, device="cpu", lora_adapter_path=None):
        self.model_path = llm_model_path
        self.device = device
        self.lora_adapter_path = lora_adapter_path
        
        if lora_adapter_path:
            logger.info(
                f"Initializing IDCardDataExtractor with base model: {self.model_path}, LoRA adapter: {lora_adapter_path}, device: {self.device}")
        else:
            logger.info(
                f"Initializing IDCardDataExtractor with model path: {self.model_path} and device: {self.device}")

        start_time = time.time()
        logger.info("Loading OCR with PaddleExtractor")
        self.paddle_extractor = PaddleExtractor()
        logger.info("PaddleExtractor loaded successfully in {} seconds".format(
            time.time() - start_time))

        start_time = time.time()
        if lora_adapter_path:
            logger.info("Loading LLMPostProcessorLoRA")
            self.llm_post_processor = LLMPostProcessorLoRA(
                base_model_path=self.model_path,
                adapter_path=lora_adapter_path
            )
            logger.info("LLMPostProcessorLoRA loaded successfully in {} seconds".format(
                time.time() - start_time))
        else:
            logger.info("Loading LLMPostProcessor")
            self.llm_post_processor = LLMPostProcessor(
                model_path=self.model_path)
            logger.info("LLMPostProcessor loaded successfully in {} seconds".format(
                time.time() - start_time))

        logger.info(
            "Initializing Prompts for different ID Card faces and formats")
        self.prompts = dict()
        self.initialize_prompts()
        logger.info("Prompts initialized successfully")

        logger.info("IDCardDataExtractor initialized successfully")

    def extract(self, image_path, id_card_version: CardVersion, side: CardSide, thinking_mode: bool = False):
        orc_results = self.paddle_extractor.extract(image_path)
        # print(orc_results.keys())
        ocr_text = " ".join(orc_results["rec_texts"])
        logger.info(f"Extracted OCR text: {ocr_text}")
        print(f"Extracted OCR text: {ocr_text}")
        
        # Select prompt based on thinking mode
        prompt_key = f"{side.name.lower()}_thinking" if thinking_mode else side
        instructions = self.prompts[id_card_version][prompt_key].format(
            ocr_text=ocr_text)
        raw_text, extracted_data = self.llm_post_processor.execute(instructions)

        return raw_text, extracted_data

    def benchmark_models(self, model_path, orc_data, id_card_version: CardVersion = CardVersion.v2018, side: CardSide = CardSide.RECTO):
        """
        Benchmark the extraction process with given OCR data.
        """
        self.llm_post_processor = LLMPostProcessor(model_path)
        instructions = self.prompts[id_card_version][side].format(
            ocr_text=orc_data)
        start_time = time.time()
        _, extracted_data = self.llm_post_processor.execute(instructions)
        elapsed_time = time.time() - start_time
        logger.info(f"Extraction completed in {elapsed_time:.2f} seconds")

        return extracted_data


    def initialize_prompts(self):
        """
        Initialize the prompts for the LLM for Cameroonian ID card data extraction.
        Each prompt is tailored for specific card version and side.
        """

        self.prompts = {
            CardVersion.v2018: {
                CardSide.RECTO: """Analyse ce texte OCR d'une carte d'identité camerounaise 2018 (RECTO) et extrait uniquement ces informations :

{ocr_text}

Retourne UNIQUEMENT ce JSON avec ces clés exactes :
{{
    "nom_surname": "Nom de famille complet",
    "prenom_given_name": "Prénom(s) complet(s)", 
    "date_of_birth": "JJ.MM.AAAA (points comme séparateurs)",
    "lieu_of_birth": "Ville/lieu de naissance",
    "sex": "M ou F uniquement",
    "taille": 1.75 (nombre décimal en mètres, sans unité),
    "profession": "Profession exacte"
}}

JSON uniquement:""",

                "recto_thinking": """<thinking>
Je dois analyser ce texte OCR d'une carte d'identité camerounaise 2018 (RECTO) et extraire les informations suivantes :
- nom_surname : Nom de famille complet
- prenom_given_name : Prénom(s) complet(s)
- date_of_birth : Format JJ.MM.AAAA avec points
- lieu_of_birth : Ville/lieu de naissance
- sex : M ou F uniquement
- taille : Nombre décimal en mètres, sans unité
- profession : Profession exacte

Analysons le texte OCR :
{ocr_text}

Je vais identifier chaque champ et extraire les données correspondantes.
</thinking>

Analyse ce texte OCR d'une carte d'identité camerounaise 2018 (RECTO) et extrait uniquement ces informations :

{ocr_text}

Retourne UNIQUEMENT ce JSON avec ces clés exactes :
{{
    "nom_surname": "Nom de famille complet",
    "prenom_given_name": "Prénom(s) complet(s)", 
    "date_of_birth": "JJ.MM.AAAA (points comme séparateurs)",
    "lieu_of_birth": "Ville/lieu de naissance",
    "sex": "M ou F uniquement",
    "taille": 1.75 (nombre décimal en mètres, sans unité),
    "profession": "Profession exacte"
}}

JSON uniquement:""",

                CardSide.VERSO: """Analyse ce texte OCR d'une carte d'identité camerounaise 2018 (VERSO) et extrait uniquement ces informations :

{ocr_text}

Retourne UNIQUEMENT ce JSON avec ces clés exactes :
{{
    "pere_father": "Nom et prénom complets du père",
    "mere_mother": "Nom et prénom complets de la mère", 
    "sp_sm": "123456 (6 chiffres exactement)",
    "date_of_issue": "JJ.MM.AAAA (points comme séparateurs)",
    "date_of_expiration": "JJ.MM.AAAA (points comme séparateurs)",
    "identifiant_unique": 20181234567890123 (17 chiffres commençant par année),
    "numero_de_carte": 123456789 (9 chiffres, nombre isolé),
    "authorité": "Martin MBARGA NGUELE ou autre autorité"
}}

JSON uniquement:""",

                "verso_thinking": """<thinking>
Je dois analyser ce texte OCR d'une carte d'identité camerounaise 2018 (VERSO) et extraire les informations suivantes :
- pere_father : Nom et prénom complets du père
- mere_mother : Nom et prénom complets de la mère
- sp_sm : 6 chiffres exactement
- date_of_issue : Format JJ.MM.AAAA avec points
- date_of_expiration : Format JJ.MM.AAAA avec points
- identifiant_unique : 17 chiffres commençant par l'année
- numero_de_carte : 9 chiffres isolés
- authorité : Généralement Martin MBARGA NGUELE

Analysons le texte OCR :
{ocr_text}

Je vais identifier chaque champ et extraire les données correspondantes.
</thinking>

Analyse ce texte OCR d'une carte d'identité camerounaise 2018 (VERSO) et extrait uniquement ces informations :

{ocr_text}

Retourne UNIQUEMENT ce JSON avec ces clés exactes :
{{
    "pere_father": "Nom et prénom complets du père",
    "mere_mother": "Nom et prénom complets de la mère", 
    "sp_sm": "123456 (6 chiffres exactement)",
    "date_of_issue": "JJ.MM.AAAA (points comme séparateurs)",
    "date_of_expiration": "JJ.MM.AAAA (points comme séparateurs)",
    "identifiant_unique": 20181234567890123 (17 chiffres commençant par année),
    "numero_de_carte": 123456789 (9 chiffres, nombre isolé),
    "authorité": "Martin MBARGA NGUELE ou autre autorité"
}}

JSON uniquement:"""
            },

            CardVersion.v2025: {
                CardSide.RECTO: """Analyse ce texte OCR d'une carte d'identité camerounaise 2025 (RECTO) et extrait uniquement ces informations :

{ocr_text}

Retourne UNIQUEMENT ce JSON avec ces clés exactes :
{{
    "numero_de_carte": 123456789 (9 chiffres au début du document),
    "nom_surname": "Nom de famille complet",
    "prenom_given_name": "Prénom(s) complet(s)",
    "date_of_birth": "JJ.MM.AAAA (points comme séparateurs)", 
    "sex": "M ou F uniquement",
    "date_of_expiration": "JJ.MM.AAAA (points comme séparateurs)"
}}

JSON uniquement:""",

                "recto_thinking": """<thinking>
Je dois analyser ce texte OCR d'une carte d'identité camerounaise 2025 (RECTO) et extraire les informations suivantes :
- numero_de_carte : 9 chiffres au début du document
- nom_surname : Nom de famille complet
- prenom_given_name : Prénom(s) complet(s)
- date_of_birth : Format JJ.MM.AAAA avec points
- sex : M ou F uniquement
- date_of_expiration : Format JJ.MM.AAAA avec points

Analysons le texte OCR :
{ocr_text}

Je vais identifier chaque champ et extraire les données correspondantes.
</thinking>

Analyse ce texte OCR d'une carte d'identité camerounaise 2025 (RECTO) et extrait uniquement ces informations :

{ocr_text}

Retourne UNIQUEMENT ce JSON avec ces clés exactes :
{{
    "numero_de_carte": 123456789 (9 chiffres au début du document),
    "nom_surname": "Nom de famille complet",
    "prenom_given_name": "Prénom(s) complet(s)",
    "date_of_birth": "JJ.MM.AAAA (points comme séparateurs)", 
    "sex": "M ou F uniquement",
    "date_of_expiration": "JJ.MM.AAAA (points comme séparateurs)"
}}

JSON uniquement:""",

                CardSide.VERSO: """Analyse ce texte OCR d'une carte d'identité camerounaise 2025 (VERSO) et extrait uniquement ces informations :

{ocr_text}

Retourne UNIQUEMENT ce JSON avec ces clés exactes :
{{
    "pere_father": "Nom et prénom complets du père",
    "mere_mother": "Nom et prénom complets de la mère",
    "lieu_of_birth": "Ville/lieu de naissance", 
    "date_of_issue": "JJ.MM.AAAA (points comme séparateurs)",
    "taille": 1.75 (nombre décimal en mètres, sans unité),
    "profession": "Profession exacte",
    "identifiant_unique": "AB12345678 (2 lettres + 8 chiffres NIC NUMBER)",
    "authorité": "Martin MBARGA NGUELE ou autre autorité"
}}

JSON uniquement:""",

                "verso_thinking": """<thinking>
Je dois analyser ce texte OCR d'une carte d'identité camerounaise 2025 (VERSO) et extraire les informations suivantes :
- pere_father : Nom et prénom complets du père
- mere_mother : Nom et prénom complets de la mère
- lieu_of_birth : Ville/lieu de naissance
- date_of_issue : Format JJ.MM.AAAA avec points
- taille : Nombre décimal en mètres, sans unité
- profession : Profession exacte
- identifiant_unique : Format AB12345678 (2 lettres + 8 chiffres)
- authorité : Généralement Martin MBARGA NGUELE

Analysons le texte OCR :
{ocr_text}

Je vais identifier chaque champ et extraire les données correspondantes.
</thinking>

Analyse ce texte OCR d'une carte d'identité camerounaise 2025 (VERSO) et extrait uniquement ces informations :

{ocr_text}

Retourne UNIQUEMENT ce JSON avec ces clés exactes :
{{
    "pere_father": "Nom et prénom complets du père",
    "mere_mother": "Nom et prénom complets de la mère",
    "lieu_of_birth": "Ville/lieu de naissance", 
    "date_of_issue": "JJ.MM.AAAA (points comme séparateurs)",
    "taille": 1.75 (nombre décimal en mètres, sans unité),
    "profession": "Profession exacte",
    "identifiant_unique": "AB12345678 (2 lettres + 8 chiffres NIC NUMBER)",
    "authorité": "Martin MBARGA NGUELE ou autre autorité"
}}

JSON uniquement:"""
            }
        }
