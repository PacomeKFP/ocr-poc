import grpc
from concurrent import futures
import tempfile
import os
import yaml
import json
import logging
from pathlib import Path

# Import generated gRPC classes (will be generated)
import ocr_service_pb2
import ocr_service_pb2_grpc

from ocr.id_card_data_extractor import IDCardDataExtractor
from ocr.card_side import CardSide
from ocr.card_version import CardVersion

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OCRServiceImpl(ocr_service_pb2_grpc.OCRServiceServicer):
    def __init__(self, config_path="config.yaml"):
        """Initialize OCR service with configuration"""
        logger.info("Initializing OCR Service...")
        
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize extractor based on config
        if self.config['model']['type'] == 'lora':
            logger.info("Using LoRA model configuration")
            self.extractor = IDCardDataExtractor(
                llm_model_path=self.config['model']['base_path'],
                lora_adapter_path=self.config['model']['lora_adapter_path']
            )
        else:
            logger.info("Using fine-tuned model configuration")
            self.extractor = IDCardDataExtractor(
                llm_model_path=self.config['model']['finetune_path']
            )
        
        # Create output directory
        os.makedirs(self.config['ocr']['output_dir'], exist_ok=True)
        
        logger.info("OCR Service initialized successfully")
    
    def ExtractData(self, request, context):
        """Process OCR extraction request"""
        try:
            logger.info(f"Received extraction request: version={request.version}, side={request.side}, thinking={request.thinking_mode}")
            
            # Save uploaded image to temp file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(request.image_data)
                temp_path = temp_file.name
            
            try:
                # Convert parameters
                card_version = CardVersion.v2018 if request.version == '2018' else CardVersion.v2025
                card_side = CardSide.RECTO if request.side == 'recto' else CardSide.VERSO
                
                # Extract data
                raw_text, extracted_data = self.extractor.extract(
                    temp_path, 
                    card_version, 
                    card_side,
                    thinking_mode=request.thinking_mode
                )
                
                # Convert extracted_data to JSON string
                if extracted_data:
                    json_data = json.dumps(extracted_data, ensure_ascii=False, indent=2)
                else:
                    json_data = "{}"
                
                logger.info("Extraction completed successfully")
                
                return ocr_service_pb2.OCRResponse(
                    success=True,
                    raw_text=raw_text,
                    extracted_data=json_data,
                    error=""
                )
                
            finally:
                # Cleanup temp file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                    
        except Exception as e:
            logger.error(f"Error during extraction: {str(e)}", exc_info=True)
            return ocr_service_pb2.OCRResponse(
                success=False,
                raw_text="",
                extracted_data="{}",
                error=str(e)
            )

def serve():
    # Load config for server settings
    with open("config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=1))  # Single worker to avoid model reloading
    
    # Add OCR service
    ocr_service_pb2_grpc.add_OCRServiceServicer_to_server(OCRServiceImpl(), server)
    
    # Start server
    listen_addr = f"{config['server']['host']}:{config['server']['port']}"
    server.add_insecure_port(listen_addr)
    
    logger.info(f"Starting OCR service on {listen_addr}")
    server.start()
    
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down OCR service...")
        server.stop(0)

if __name__ == '__main__':
    serve()