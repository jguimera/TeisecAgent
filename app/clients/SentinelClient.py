import requests
import json
import uuid
import os
from datetime import datetime, timezone, timedelta
import pandas as pd
from azure.identity import ClientSecretCredential,UsernamePasswordCredential 
from azure.monitor.query import LogsQueryClient,LogsQueryStatus
from azure.core.exceptions import (
    ClientAuthenticationError,
    HttpResponseError,
    ServiceRequestError,
    ResourceNotFoundError,
    AzureError
)
class SentinelClient:
    login_url="https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    API_url="https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.OperationalInsights/workspaces/{workspaceName}/providers/Microsoft.SecurityInsights/"
    API_query_url="https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.OperationalInsights/workspaces/{workspaceName}/providers/Microsoft.Insights/"
    API_management_url="https://management.azure.com"
    API_versionOLD="2021-03-01-preview"
    API_version_incidents="2021-04-01"
    API_version_rules="2021-10-01"
    API_version_logs="2018-08-01-preview"
    API_version_templates="2023-02-01"
    scope="https://management.azure.com/.default"

    def __init__(self,credential,subscriptionId,resourceGroupName,workspaceName,workspace_id):

        self.subscriptionId = subscriptionId
        self.resourceGroupName = resourceGroupName
        self.workspaceName = workspaceName
        self.workspace_id=workspace_id
        self.access_token_timestamp=0
        self.credential=credential
        self.logs_client=LogsQueryClient(self.credential)

    def run_query(self,query,printresults=False):
        results_object={}
        try:
            response = self.logs_client.query_workspace(
                workspace_id=self.workspace_id,
                query=query,
                #timespan=timedelta(days=1)
                timespan=None
                )
            if response.status == LogsQueryStatus.PARTIAL:
                error = response.partial_error
                data = response.partial_data
                print(error.message)
            elif response.status == LogsQueryStatus.SUCCESS:
                data = response.tables
            for table in data:
                df = pd.DataFrame(data=table.rows, columns=table.columns)
                if printresults:
                    print(df)
                #return df.to_json(orient = 'split')
                results_object={"status":"success","result":df.to_dict(orient="records")}
        except HttpResponseError as err:
            results_object={"status":"error","result":err}
        return results_object
    def _get_incident_api_url (self,incident_name):
        url = self.API_url.replace("{subscriptionId}",self.subscriptionId).replace("{resourceGroupName}",self.resourceGroupName).replace("{workspaceName}",self.workspaceName)
        url=url+"incidents/"+incident_name+"?api-version="+self.API_version_incidents
        return url 
    def _get_rules_api_url (self):
        url = self.API_url.replace("{subscriptionId}",self.subscriptionId).replace("{resourceGroupName}",self.resourceGroupName).replace("{workspaceName}",self.workspaceName)
        url=url+"alertRules?api-version="+self.API_version_rules
        return url
    def _get_ruletemplates_api_url (self):
        url = self.API_url.replace("{subscriptionId}",self.subscriptionId).replace("{resourceGroupName}",self.resourceGroupName).replace("{workspaceName}",self.workspaceName)
        url=url+"alertRuleTemplates?api-version="+self.API_version_templates
        return url
    def _get_rule_api_url (self,ruleName):
        url = self.API_url.replace("{subscriptionId}",self.subscriptionId).replace("{resourceGroupName}",self.resourceGroupName).replace("{workspaceName}",self.workspaceName)
        url=url+"alertRules/"+ruleName+"?api-version="+self.API_version_rules
        return url
    def _get_access_token (self):
        now_ts=datetime.now().timestamp()
        self.access_token=self.credential.get_token("https://management.azure.com/.default").token
        self.access_token_timestamp=now_ts
        return self.access_token
        
    def get_alerts (self):
        print ("Invoking Alerts API - Get Alert Rule")
        access_token=self._get_access_token()
        url = self._get_rules_api_url()
        headers = {
           'authorization': 'Bearer ' + access_token
        }
        response = requests.request("GET", url, headers=headers)
        return response.json()
    def get_alerttemplates (self):
        print ("Invoking Alerts API - Get Alert Rule Template")
        access_token=self._get_access_token()
        url = self._get_ruletemplates_api_url()
        headers = {
           'authorization': 'Bearer ' + access_token
        }
        response = requests.request("GET", url, headers=headers)
        return response.json()
        
    def get_incident (self,incident_name):
        print ("Invoking Incidents API - Get Incident")
        access_token=self._get_access_token()
        url = self._get_incident_api_url(incident_name)
        headers = {
           'authorization': 'Bearer ' + access_token
        }
        response = requests.request("GET", url, headers=headers)
        incident=response.json()
        return incident
    def update_incident (self,incident):
        print ("Invoking Incidents API - Get Incident")
        incident_name=incident["name"]
        access_token=self._get_access_token()
        url = self._get_incident_api_url(incident_name)
        headers = {
           'authorization': 'Bearer ' + access_token,
           'Content-Type': 'application/json'
        }
        response = requests.request("PUT", url, headers=headers,data=json.dumps(incident))
        return response.json()