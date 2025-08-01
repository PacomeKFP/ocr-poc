from typing import Dict, List
from card_side import CardSide
from card_version import CardVersion
from paddle_extractor import PaddleExtractor
from new_post_extraction_parser import NewPostExtractionParser
from old_post_extraction_parser import OldPostExtractionParser
from simple_extractor import SimplifiedCNIExtractor


class Extractor:
    def __init__(self):
        self.paddle_extractor = PaddleExtractor()
        self.new_post_parser = NewPostExtractionParser()
        self.old_post_parser = OldPostExtractionParser()
        self.simple_extractor = SimplifiedCNIExtractor()

    def extract(self, image_path: str, version: CardVersion = CardVersion.v2018, side: CardSide = CardSide.RECTO) -> List[Dict]:
        ocr_result = self.paddle_extractor.extract(image_path)
        if version == CardVersion.v2025:
            return self.new_post_parser.parse(ocr_result[0], side=side)["extracted_fields"]
        else:
            return self.old_post_parser.parse(ocr_result[0], side=side)["extracted_fields"]

    def extract_many(self, image_paths: List[str], version: CardVersion = CardVersion.v2018, sides: List[CardSide] = [CardSide.RECTO, CardSide.VERSO]) -> List[Dict]:
        ocr_results = self.paddle_extractor.extract(image_paths)
        if version == CardVersion.v2025:
            return [self.new_post_parser.parse(result, side=side)["extracted_fields"] for result, side in zip(ocr_results, sides)]
        else:
            return [self.old_post_parser.parse(result, side=side)["extracted_fields"] for result, side in zip(ocr_results, sides)]
