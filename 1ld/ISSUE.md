INFO:werkzeug:127.0.0.1 - - [01/Aug/2025 10:58:15] "GET / HTTP/1.1" 200 -
INFO:__main__:=== DÉBUT UPLOAD REQUEST ===
INFO:__main__:Fichier reçu: ID Card Kengali Fegue Pacome_1.jpg, Version: 2018, Side: recto
INFO:__main__:Sauvegarde du fichier: uploads\ID_Card_Kengali_Fegue_Pacome_1.jpg
INFO:__main__:Vérification de l'extracteur...
INFO:__main__:Initializing IDCardDataExtractor with LoRA adapter at startup...
INFO:ocr.id_card_data_extractor:Initializing IDCardDataExtractor with base model: ./models/Qwen/Qwen3-0.6B, LoRA adapter: ./models/finetunes/qwen3-0.6b-cni-lora/checkpoint-938, device: cpu
INFO:ocr.id_card_data_extractor:Loading OCR with PaddleExtractor
Information : impossible de trouver des fichiers pour le(s) modèle(s) spécifié(s).
C:\Users\xrbj6161\AppData\Local\Programs\Python\Python311\Lib\site-packages\paddle\utils\cpp_extension\extension_utils.py:715: UserWarning: No ccache found. Please be aware that recompiling all source files may be required. You can download and install ccache from: https://github.com/ccache/ccache/blob/master/doc/INSTALL.md
  warnings.warn(warning_message)
Creating model: ('PP-LCNet_x1_0_doc_ori', None)
Using official model (PP-LCNet_x1_0_doc_ori), the model files will be automatically downloaded and saved in C:\Users\xrbj6161\.paddlex\official_models.
Creating model: ('UVDoc', None)
The model(UVDoc) is not supported to run in MKLDNN mode! Using `paddle` instead!
Using official model (UVDoc), the model files will be automatically downloaded and saved in C:\Users\xrbj6161\.paddlex\official_models.
Creating model: ('PP-LCNet_x1_0_textline_ori', None)
Using official model (PP-LCNet_x1_0_textline_ori), the model files will be automatically downloaded and saved in C:\Users\xrbj6161\.paddlex\official_models.
Creating model: ('PP-OCRv5_server_det', None)
Using official model (PP-OCRv5_server_det), the model files will be automatically downloaded and saved in C:\Users\xrbj6161\.paddlex\official_models.
Creating model: ('PP-OCRv5_server_rec', None)
Using official model (PP-OCRv5_server_rec), the model files will be automatically downloaded and saved in C:\Users\xrbj6161\.paddlex\official_models.
Chargement du modèle de base... ./models/Qwen/Qwen3-0.6B
Chargement de l'adaptateur LoRA... ./models/finetunes/qwen3-0.6b-cni-lora/checkpoint-938
Chargement du modèle de base...
Chargement de l'adaptateur LoRA...
WARNING:bitsandbytes.cextension:The installed version of bitsandbytes was compiled without GPU support. 8-bit optimizers and GPU quantization are unavailable.
Adaptateur LoRA chargé avec succès.
Modèle LoRA chargé et prêt pour l'inférence CPU.
