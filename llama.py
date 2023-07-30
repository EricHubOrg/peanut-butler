from transformers import AutoTokenizer, AutoModelForCausalLM
import os, logging, json

logging.basicConfig(level=logging.INFO)

dir_path = '/data/llama-2-13b-chat'

if os.path.exists(dir_path) and os.path.isdir(dir_path):
	logging.info(f'Loading model from {dir_path}')
	try:
		tokenizer = AutoTokenizer.from_pretrained(dir_path)
		model = AutoModelForCausalLM.from_pretrained(dir_path)
		logging.info(f'Model loaded correctly. Size: {model.get_memory_footprint()}')
	except Exception as e:
		logging.info(f'Error loading model: {e}')
else:
	logging.info(f"Path {dir_path} doesn't exist in the root directory. Model couldn't be loaded")

def generate(prompt):
	logging.info(f'Loading generation config from {dir_path}/generation_config.json')
	try:
		with open(dir_path+'/generation_config.json') as f:
			generation_config = json.load(f)
		logging.info('Generation config loaded correctly')
	except Exception as e:
		logging.info(f'Error loading generation config: {e}')
	logging.info('Tokenizing prompt...')
	inputs = tokenizer(prompt, return_tensors='pt')
	logging.info('Generating response...')
	outputs = model.generate(**inputs, **generation_config)
	logging.info('Decoding response...')
	decoded_output = tokenizer.decode(outputs[0], skip_special_tokens=True, clean_up_tokenization_spaces=True)
	logging.info('Sending response...')
	return decoded_output