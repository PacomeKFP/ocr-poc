import time
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import json
import re

# Mesure du temps de chargement du modèle
start_load = time.time()
model_id = "./models/finetunes/qwen3-0.6b-lora-cni-2018-front"  # ou ton fine-tune local

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id, torch_dtype=torch.float16)
model.eval()
end_load = time.time()
print(f"Temps de chargement du modèle : {end_load - start_load:.2f} secondes")

# Ton prompt
prompt = """
REPUBLIC OF CAMEROON NOM/SURNAME OROKO PRENOMS/GIVEN NAMES HANNAH 09.05.1991 CARTE NATIONALE D'IDENTITÉ LIEU DE NAISSANCE/PLACE OF BIRTH SEXE/SEX OLAMA F TAILLE/HEIGHT 1.59 DOCKER SIGNATURE DGSN
Extrais les informations suivantes au format JSON :
{
    "nom_surname": "",
    "prenom_given_name": "",
    "date_of_birth": "",
    "lieu_of_birth": "",
    "sex": "",
    "taille": "",
    "profession": ""
}
"""

# Génération de texte
start_gen = time.time()
inputs = tokenizer(prompt, return_tensors="pt")
with torch.no_grad():
    outputs = model.generate(**inputs, max_new_tokens=100)
generated_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
end_gen = time.time()
print(f"Temps d'exécution de la requête : {end_gen - start_gen:.2f} secondes")

# Extraction du JSON depuis le texte généré
match = re.search(r'\{.*\}', generated_text, re.DOTALL)
if match:
    try:
        output_json = json.loads(match.group())
    except Exception:
        output_json = match.group()
else:
    output_json = "Aucun JSON trouvé."

print(output_json)

print(f"Texte généré : {generated_text}")
