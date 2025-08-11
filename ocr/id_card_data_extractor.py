from ocr.extractors.cni_extractor_18_b import CNIExtractor18B
from ocr.extractors.cni_extractor_18_f import CNIExtractor18F
from ocr.extractors.cni_extractor_25_b import CNIExtractor25B
from ocr.extractors.cni_extractor_25_f import CNIExtractor25F
from ocr.card_side import CardSide
from ocr.card_version import CardVersion
from ocr.paddle_extractor import PaddleExtractor
import logging
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IDCardDataExtractor:
    def __init__(self):
               
        start_time = time.time()
        logger.info("Loading OCR with PaddleExtractor")
        self.paddle_extractor = PaddleExtractor()
        logger.info("PaddleExtractor loaded successfully in {} seconds".format(
            time.time() - start_time))

        logger.info("Initializing Extractors")
        self.cni_extractor = {
            CardVersion.v2018: 
            {
                CardSide.RECTO: CNIExtractor18F(),
                CardSide.VERSO: CNIExtractor18B()
            },
            CardVersion.v2025: {
                CardSide.RECTO: CNIExtractor25F(),
                CardSide.VERSO: CNIExtractor25B()
            }
        }
        

        logger.info("IDCardDataExtractor initialized successfully")

    def extract(self, image_path, id_card_version: CardVersion, side: CardSide):
        start_time = time.time()
        logger.info(f"Using OCR to detect and recog text from image: {image_path}")
        ocr_results = self.paddle_extractor.extract(image_path)
        ocr_text = " ".join(ocr_results["rec_texts"])
        logger.info(f"OCR done in {time.time() - start_time} seconds \n text output: {ocr_text}")

        start_time = time.time()
        logger.info(f"Using cni_extractor to extract text for side {side} and version {id_card_version}")
        extracted_data = self.cni_extractor[id_card_version][side].extract(ocr_results)
        logger.info('Extraction completed in {} secs'.format(time.time() - start_time))

        return ocr_text, extracted_data
