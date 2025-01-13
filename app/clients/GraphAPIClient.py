import requests
import json
import uuid
import os
from datetime import datetime, timezone, timedelta
from azure.identity import ClientSecretCredential,UsernamePasswordCredential 
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ServiceRequestError,
    ResourceNotFoundError,
    AzureError
)
class GraphAPIClient:
    login_url="https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    API_base_url="https://graph.microsoft.com/v1.0"
    scope="https://graph.microsoft.com/.default"

    def __init__(self,credential):

        self.access_token_timestamp=0
        self.credential=credential

    def _get_access_token (self):
        now_ts=datetime.now().timestamp()
        self.access_token=self.credential.get_token(self.scope).token
        self.access_token_timestamp=now_ts
        return self.access_token
        
    def get_email (self,mailbox,internetmessageid):
        print ("Invoking Graph API - Get Email")
        access_token=self._get_access_token()
        url = self.API_base_url+'/users/'+mailbox+"/messages?$select=subject,body,internetMessageHeaders&$filter=internetMessageId eq '"+internetmessageid+"'"
        print(url)
        headers = {
           'authorization': 'Bearer ' + access_token
        }
        response = requests.request("GET", url, headers=headers)
        
        if response.status_code == 200:
            result_object={ "status":"success","result":response.json(),"session_tokens":0}
            return result_object
        else:
            error_message=f"Error: {response.status_code} - {response.text}"
            print(error_message)
            result_object={ "status":"error","result":error_message,"session_tokens":0}