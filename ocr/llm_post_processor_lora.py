import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import logging

logger = logging.getLogger(__name__)

class LLMPostProcessorLoRA:
    """
    Post-processor for Large Language Model (LLM) outputs with LoRA adapter support.
    This class is responsible for processing the raw outputs from the LLM
    to make them suitable for further use or analysis.
    Optimized for CPU-only inference without quantization.
    """

    def __init__(self, base_model_path, adapter_path):
        """
        Initialize the LLM post-processor with LoRA adapter.
        
        Args:
            base_model_path: Path to the base model (e.g., Qwen3-0.6B)
            adapter_path: Path to the LoRA adapter checkpoint
        """
        print(f"Chargement du modèle de base... {base_model_path}")
        print(f"Chargement de l'adaptateur LoRA... {adapter_path}")

        # Force CPU usage
        self.device = "cpu"
        
        # Load tokenizer from base model
        self.tokenizer = AutoTokenizer.from_pretrained(
            base_model_path, 
            trust_remote_code=True
        )
        
        # Load base model for CPU without quantization
        print("Chargement du modèle de base...")
        self.base_model = AutoModelForCausalLM.from_pretrained(
            base_model_path,
            torch_dtype=torch.float32,  # Use float32 for CPU
            low_cpu_mem_usage=True,
            trust_remote_code=True,
            device_map=None  # Let PEFT handle device placement
        )
        
        # Load LoRA adapter
        print("Chargement de l'adaptateur LoRA...")
        try:
            self.model = PeftModel.from_pretrained(
                self.base_model,
                adapter_path,
                torch_dtype=torch.float32
            )
            logger.info(f"LoRA adapter successfully loaded from {adapter_path}")
            print("Adaptateur LoRA chargé avec succès.")
        except Exception as e:
            logger.error(f"Failed to load LoRA adapter: {e}")
            print(f"Erreur lors du chargement de l'adaptateur LoRA: {e}")
            # Fallback to base model if adapter loading fails
            self.model = self.base_model
            print("Repli sur le modèle de base.")
        
        # Move to CPU
        self.model.to(self.device)
        
        # Set pad token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        print("Modèle LoRA chargé et prêt pour l'inférence CPU.")
    
    def execute(self, instructions):
        """
        Process the raw output from the LLM with LoRA adapter.

        Args:
            instructions: The instructions/prompt for the LLM.

        Returns:
            Tuple (raw_text, parsed_json): Raw generated text and parsed JSON (or None if parsing fails).
        """
        logger.debug(f"Processing instructions: {instructions[:100]}...")
        
        # Tokenize input
        inputs = self.tokenizer(instructions, return_tensors="pt").to(self.device)
        
        # Generate with optimized settings for CPU
        logger.info("Début génération LLM...")
        with torch.no_grad():
            try:
                logger.info("Appel du modèle pour génération...")
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=200,
                    temperature=0.3,  # Lower temperature for more deterministic output
                    do_sample=True,
                    pad_token_id=self.tokenizer.pad_token_id,
                    eos_token_id=self.tokenizer.eos_token_id,
                    use_cache=True,  # Enable KV cache for efficiency
                    num_beams=1,  # Greedy search for speed
                )
                logger.info("Génération LLM terminée avec succès")
            except Exception as e:
                logger.error(f"Generation failed: {e}", exc_info=True)
                return f"Erreur lors de la génération: {e}", None

        # Decode response
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        generated_text = response[len(instructions):].strip()
        
        logger.debug(f"Generated text: {generated_text[:200]}...")
        
        # Extract JSON from the generated text
        first_opening = generated_text.find("{")
        first_closure = generated_text.find("}")
        
        if first_closure != -1 and first_opening != -1 and first_closure > first_opening:
            json_text = generated_text[first_opening:first_closure + 1]
            try:
                parsed_json = json.loads(json_text)
                logger.info("JSON successfully parsed from generated text")
                return generated_text, parsed_json
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {e}")
                logger.debug(f"Attempted to parse: {json_text}")
                return generated_text, None
        else:
            logger.warning("No valid JSON structure found in generated text")
        
        return generated_text, None
    
    def get_model_info(self):
        """
        Get information about the loaded model and adapter.
        
        Returns:
            dict: Model information
        """
        info = {
            "device": self.device,
            "base_model": getattr(self.base_model, "name_or_path", "Unknown"),
            "has_adapter": hasattr(self.model, "peft_config"),
            "model_type": type(self.model).__name__
        }
        
        if hasattr(self.model, "peft_config"):
            peft_config = list(self.model.peft_config.values())[0]
            info.update({
                "adapter_type": peft_config.peft_type.value,
                "lora_r": getattr(peft_config, "r", None),
                "lora_alpha": getattr(peft_config, "lora_alpha", None),
                "target_modules": getattr(peft_config, "target_modules", None)
            })
        
        return info