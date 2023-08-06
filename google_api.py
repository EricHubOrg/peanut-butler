import os.path
import logging

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# if modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_credentials():
	creds = None
	# the file token.json stores the user's access and refresh tokens, and is
	# created automatically when the authorization flow completes for the first
	# time.
	if os.path.exists(f'{os.environ["DATA_PATH"]}/gmail/token.json'):
		creds = Credentials.from_authorized_user_file(f'{os.environ["DATA_PATH"]}/gmail/token.json', SCOPES)
	# if there are no (valid) credentials available, let the user log in.
	if not creds or not creds.valid:
		if creds and creds.expired and creds.refresh_token:
			logging.info('Refreshing credentials...')
			creds.refresh(Request())
		else:
			logging.info('Requesting new credentials...')
			try:
				flow = InstalledAppFlow.from_client_secrets_file(
					f'{os.environ["DATA_PATH"]}/gmail/credentials.json', SCOPES)
				creds = flow.run_local_server(port=0)
			except Exception as e:
				logging.info(f'Error requesting credentials: {e}')
				return None
		# save the credentials for the next run
		logging.info('Saving credentials as token...')
		with open(f'{os.environ["DATA_PATH"]}/gmail/token.json', 'w') as token:
			token.write(creds.to_json())
		logging.info('Credentials saved successfully')
	
	return creds