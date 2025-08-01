from paddleocr import PaddleOCR
from typing import List


class PaddleExtractor:
    """
    PaddleOCR extractor for OCR tasks.
    """

    def __init__(self):
        """
        Initialize the PaddleOCR extractor with the specified language.

        :param lang: Language for OCR, default is 'en'.
        """
        self.ocr = PaddleOCR(
            use_doc_orientation_classify=True,
            use_doc_unwarping=True,
            use_textline_orientation=True
        )

    def extract(self, image_path: str):
        """
        Extract text from the given image path.

        :param image_path: Path to the image file.
        :return: List of detected text and their bounding boxes.
        """
        return self.ocr.predict(image_path)

    def extract_many(self, image_paths: List[str]):
        """
        Extract text from multiple images.

        :param image_paths: List of paths to the image files.
        :return: List of detected text and their bounding boxes for each image.
        """
        
        return self.ocr.predict_iter(image_paths)
