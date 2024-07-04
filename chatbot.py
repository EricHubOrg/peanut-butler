import json, logging, aiohttp

logging.basicConfig(level=logging.INFO)

async def generate(prompt, conversation, api_url, api_key):
	input_data = {'inputs': {'text':prompt, 'past_user_inputs':conversation['past_user_inputs'], 'generated_responses':conversation['generated_responses']}}

	if not api_key:
		raise Exception('A key should be provided to invoke the endpoint')

	headers = {'Content-Type':'application/json', 'Authorization':('Bearer '+ api_key), 'azureml-model-deployment': 'facebook-blenderbot-3b' }

	logging.info('Sending request to endpoint, waiting for response...')
	async with aiohttp.ClientSession() as session:
		async with session.post(api_url, data=json.dumps(input_data), headers=headers) as response:
			if response.status != 200:
				logging.info(f'The request failed with status code: {response.status}')
				logging.info(await response.text())
				return None, None

			result = await response.json()
			logging.info('Response received. Sending...')
			return result['generated_text'], result['conversation']