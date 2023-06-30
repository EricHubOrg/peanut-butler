# import os.path

# from google.auth.transport.requests import Request
# from google.oauth2.credentials import Credentials
# from google_auth_oauthlib.flow import InstalledAppFlow

# # if modifying these scopes, delete the file token.json.
# SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# def get_credentials():
# 	creds = None
# 	# the file token.json stores the user's access and refresh tokens, and is
# 	# created automatically when the authorization flow completes for the first
# 	# time.
# 	if os.path.exists('token.json'):
# 		creds = Credentials.from_authorized_user_file('token.json', SCOPES)
# 	# if there are no (valid) credentials available, let the user log in.
# 	if not creds or not creds.valid:
# 		if creds and creds.expired and creds.refresh_token:
# 			creds.refresh(Request())
# 		else:
# 			flow = InstalledAppFlow.from_client_secrets_file(
# 				'credentials.json', SCOPES)
# 			creds = flow.run_local_server(port=0)
# 		# save the credentials for the next run
# 		with open('token.json', 'w') as token:
# 			token.write(creds.to_json())
			
# 	return creds