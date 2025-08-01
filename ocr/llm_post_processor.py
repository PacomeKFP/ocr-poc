import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

class LLMPostProcessor:
    """
    Post-processor for Large Language Model (LLM) outputs.
    This class is responsible for processing the raw outputs from the LLM
    to make them suitable for further use or analysis.
    """

    def __init__(self, model_path):
        print(f"Chargement du modèle... {model_path}")

        quant_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            load_in_8bit=False  # Only load in 4bit or 8bit, not both
        )

        
        # Charger le modèle
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            quantization_config=quant_config if torch.cuda.is_available() else None,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            low_cpu_mem_usage=True,
            trust_remote_code=True
        ).to(self.device)


        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        print("Modèle chargé.")
    
    def execute(self, instructions):
        """
        Process the raw output from the LLM.

        Args:
            instructions: The instructions/prompt for the LLM.

        Returns:
            Tuple (raw_text, parsed_json): Raw generated text and parsed JSON (or None if parsing fails).
        """
        inputs = self.tokenizer(instructions, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=200,
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id
            )

        # Résultat
        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        generated_text = response[len(instructions):].strip()
        
        # Extract JSON from the generated text
        first_opening = generated_text.find("{")
        first_closure = generated_text.find("}")
        
        if first_closure != -1 and first_opening != -1 and first_closure > first_opening:
            json_text = generated_text[first_opening:first_closure + 1]
            try:
                parsed_json = json.loads(json_text)
                return generated_text, parsed_json
            except json.JSONDecodeError:
                return generated_text, None
        
        return generated_text, None