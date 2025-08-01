from paddleocr import PaddleOCR
from typing import List
import os
import uuid


class PaddleExtractor:
    """
    PaddleOCR extractor for OCR tasks.
    """

    def __init__(self, output_dir="ocr_outputs"):
        """
        Initialize the PaddleOCR extractor with the specified language.

        :param output_dir: Directory to save OCR results and images.
        """
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.ocr = PaddleOCR(
            use_doc_orientation_classify=True,
            use_doc_unwarping=True,
            use_textline_orientation=True
        )

    def extract(self, image_path: str):
        """
        Extract text from the given image path and save results.

        :param image_path: Path to the image file.
        :return: List of detected text and their bounding boxes.
        """
        result = self.ocr.predict(image_path)
        
        # Générer un nom unique pour les fichiers de sortie
        unique_id = str(uuid.uuid4())[:8]
        base_name = os.path.splitext(os.path.basename(image_path))[0]
        output_name = f"{base_name}_{unique_id}"
        
        # Sauvegarder les résultats
        for i, res in enumerate(result):
            output_path = os.path.join(self.output_dir, f"{output_name}_{i}")
            res.save_to_img(output_path)
            res.save_to_json(output_path)
        
        return result[0]

    def extract_many(self, image_paths: List[str]):
        """
        Extract text from multiple images.

        :param image_paths: List of paths to the image files.
        :return: List of detected text and their bounding boxes for each image.
        """
        
        return self.ocr.predict_iter(image_paths)
