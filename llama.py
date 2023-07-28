from transformers import AutoTokenizer, AutoModelForCausalLM

tokenizer = AutoTokenizer.from_pretrained("llama2")
model = AutoModelForCausalLM.from_pretrained("llama2")

def generate(prompt, max_length=50):
	inputs = tokenizer(prompt, return_tensors="pt")
	generate_ids = model.generate(inputs.input_ids, max_length=max_length)
	return tokenizer.batch_decode(generate_ids, skip_special_tokens=True, clean_up_tokenization_spaces=False)[0]