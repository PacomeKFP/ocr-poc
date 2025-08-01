import torch
from ocr.llm_post_processor import LLMPostProcessor
from ocr.card_side import CardSide
from ocr.card_version import CardVersion
# from ocr.paddle_extractor import PaddleExtractor
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IDCardDataExtractor:
    def __init__(self, llm_model_path, device="cpu"):
        self.model_path = llm_model_path
        self.device = device
        logger.info(
            f"Initializing IDCardDataExtractor with model path: {self.model_path} and device: {self.device}")

        start_time = time.time()
        logger.info("Loading OCR with PaddleExtractor")
        # self.paddle_extractor = PaddleExtractor()
        self.paddle_extractor = None
        logger.info("PaddleExtractor loaded successfully in {} seconds".format(
            time.time() - start_time))

        start_time = time.time()
        logger.info("Loading LLMPostProcessor")
        self.llm_post_processor: LLMPostProcessor = LLMPostProcessor(
            model_path=self.model_path)
        logger.info("LLMPostProcessor loaded successfully in {} seconds".format(
            time.time() - start_time))

        logger.info(
            "Initializing Prompts for different ID Card faces and formats")
        self.prompts = dict()
        self.initialize_prompts()
        logger.info("Prompts initialized successfully")

        logger.info("IDCardDataExtractor initialized successfully")

    def extract(self, image_path, id_card_version: CardVersion, side: CardSide):
        # orc_results = self.paddle_extractor.extract(image_path)
        ocr_text = " ".join(orc_results["rec_texts"])
        instructions = self.prompts[id_card_version][side].format(
            ocr_text=ocr_text)
        extracted_data = self.llm_post_processor.execute(instructions)

        return extracted_data

    def benchmark_models(self, model_path, orc_data, id_card_version: CardVersion = CardVersion.v2018, side: CardSide = CardSide.RECTO):
        """
        Benchmark the extraction process with given OCR data.
        """
        self.llm_post_processor = LLMPostProcessor(model_path)
        instructions = self.prompts[id_card_version][side].format(
            ocr_text=orc_data)
        start_time = time.time()
        extracted_data = self.llm_post_processor.execute(instructions)
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
                CardSide.RECTO: """Extract information from this Cameroonian ID card text and format as JSON:
                    {ocr_text}
                    Extract: nom/surname, prenoms/given_names, date_naissance, lieu_naissance, sexe, taille, profession
                    JSON (only, no explanation, only the json object):""",

                CardSide.VERSO: """Extrait les informations de cette carte d'identité camerounaise (verso 2018). Texte OCR:
                {ocr_text}

                Retourne uniquement un JSON avec ces clés exactes:
                {{
                    "pere_father": "nom et prénom du père",
                    "mere_mother": "nom et prénom de la mère",
                    "sp_sm": "nombre à 6 chiffres",
                    "date_of_issue": "JJ.MM.AAAA",
                    "date_of_expiration": "JJ.MM.AAAA",
                    "identifiant_unique": 20181234567890123,
                    "numero_de_carte": 123456789,
                    "authorité": "nom de l'autorité"
                }}

                JSON uniquement:""",
            },

            CardVersion.v2025: {
                CardSide.RECTO: """Extrait les informations de cette carte d'identité camerounaise (recto 2025). Texte OCR:
                {ocr_text}

                Retourne uniquement un JSON avec ces clés exactes:
                {{
                    "numero_de_carte": 123456789,
                    "nom_surname": "nom et prénom de famille",
                    "prenom_given_name": "prénom(s)",
                    "date_of_birth": "JJ.MM.AAAA",
                    "sex": "M ou F",
                    "date_of_expiration": "JJ.MM.AAAA"
                }}

                JSON uniquement:""",

                CardSide.VERSO: """Extrait les informations de cette carte d'identité camerounaise (verso 2025). Texte OCR:
                {ocr_text}

                Retourne uniquement un JSON avec ces clés exactes:
                {{
                    "pere_father": "nom et prénom du père",
                    "mere_mother": "nom et prénom de la mère",
                    "lieu_of_birth": "lieu de naissance",
                    "date_of_issue": "JJ.MM.AAAA",
                    "taille": 1.75,
                    "profession": "profession",
                    "identifiant_unique": "AB12345678",
                    "authorité": "nom de l'autorité"
                }}

                JSON uniquement:"""
            }
        }
