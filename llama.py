from transformers import AutoTokenizer, AutoModelForCausalLM
import os, logging

logging.basicConfig(level=logging.INFO)

dir_path = "/data/data/llama2"

logging.info(f"Files and directories in root directory: {os.listdir('/')}")
logging.info(f"Files and directories in /data/data directory: {os.listdir('/data/data')}")

if os.path.exists(dir_path) and os.path.isdir(dir_path):
	logging.info(f"Loading model from {dir_path}")
	tokenizer = AutoTokenizer.from_pretrained(dir_path)
	model = AutoModelForCausalLM.from_pretrained(dir_path)

def generate(prompt, max_length=50):
	inputs = tokenizer(prompt, return_tensors="pt")
	generate_ids = model.generate(inputs.input_ids, max_length=max_length)
	return tokenizer.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]