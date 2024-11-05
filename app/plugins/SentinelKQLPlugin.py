from app.plugins.TeisecAgentPlugin import TeisecAgentPlugin  
from colorama import Fore  
import json  
import os  
from app.HelperFunctions import print_plugin_debug  
  
class SentinelKQLPlugin(TeisecAgentPlugin):  
    """  
    Plugin to generate and run KQL queries adhering to the Sentinel schema.  
    """  
  
    def __init__(self, name, description, plugintype, azureOpenAIClient, sentinelClient, loadSchema=True):  
        """  
        Initialize the SentinelKQLPlugin.  
  
        :param name: Name of the plugin  
        :param description: Description of the plugin  
        :param plugintype: Type of the plugin  
        :param azureOpenAIClient: Azure OpenAI Client instance  
        :param sentinelClient: Sentinel Client instance  
        :param loadSchema: Boolean to determine if the schema should be loaded  
        """  
        super().__init__(name, description, plugintype)  
        self.azureOpenAIClient = azureOpenAIClient  
        self.sentinelClient = sentinelClient  
        self.loadSchema = loadSchema  
        self.default_schema_file = 'sentinel_extended_schema.json'
        self.sentinel_schema = None  
        if loadSchema:  
            self.sentinel_schema = self.loadSentinelSchema()  
  
    def pluginhelp(self):  
        """  
        Provide help instructions for this plugin.  
  
        :return: Help instructions string  
        """  
        return "Use 'kql' in your prompt to generate and run KQL adhering to the Sentinel schema."  
    def plugincapabilities(self):  
        """  
        Provide the plugin capabilities.  
  
        :return: plugin capabilities object  
        """  
        capabilities={
            "generateandrunkql":"This capability allows to generate and run one KQL query to retrieve logs and events from Microsoft Sentinel. This capability should be used when the user asks about retrieving new incidents, alerts or any other data that is not already in the context or needs to be retrieved from and external url. Other type of common data retrieved by this capabilitiy are Signin, Audit, Device, Email and Azure logs. Do not use this capabilitiy if the user ask for only KQL generation without runing it"
            ,"onlygeneratekql":"This capability allows to generate one KQL query for Microsoft Sentinel without runing the query. This capability should be used when the user asks about only generating a query for Sentinel without running it."
            ,"extractandrunkql":"This capability allows to extract and run one KQL query for Microsoft Sentinel from the user prompt or the session. This capability should be used when the user asks for extraction of a query or tu run a specific predefined query."
            }
        return  capabilities
  
    def generateSentinelSchema(self):  
        """  
        Retrieve and store the schema of Azure Sentinel tables.  
        """  
        query = "Usage | summarize by DataType"
        query_results_object = self.sentinelClient.run_query(query, printresults=False) 
        if query_results_object['status']=='error':
            print_plugin_debug(self.name, f"Error obtaining Table lists. No using Schema for Table generation") 
            return {}
        query_results=query_results_object['result']
        current_consolidated_schema = {}  
        default_schema = {} 
        workspace_schema = {} 
        print_plugin_debug(self.name, f"Retrieving Sentinel Schema for Workspace tables ({len(query_results)})")  
        current_workspace_name=self.sentinelClient.workspaceName
        try:
            with open(current_workspace_name+'.json', 'r', encoding='utf-8') as f:  
                workspace_schema=json.load(f) 
        except Exception as err:
            print_plugin_debug(self.name, f"No Workspace schema found for workspace {current_workspace_name}. Creating one.")  
        with open(self.default_schema_file, 'r', encoding='utf-8') as f:  
            default_schema=json.load(f) 
        #Consolidate Default and Workspace Schema
        global_schema=default_schema | workspace_schema
        #Process each available table and add it to the consolidated schema or generate the workspace schema entry using AI.
        for table in query_results:  
            table_name=table['DataType']
            if table_name in global_schema.keys():
                current_consolidated_schema[table_name]=global_schema[table_name]
                print_plugin_debug(self.name, f"Found Table  {table_name} in existing schemas. Added to Consolidated")
            else:
                print_plugin_debug(self.name, f"Table  {table_name} not found in existing schemas. Generating schema and saving in Workspace custom Schema.")
                table_schema = f"{table_name} | getschema kind=csl"
                try:
                    table_schema_results_object = self.sentinelClient.run_query(table_schema, printresults=False)
                    current_table_schema = table_schema_results_object['result'][0]['Schema']  
                    table_rows_query = f"{table_name} | where TimeGenerated > ago(30d) |take 3"  
                    table_rows_query_result_object = self.sentinelClient.run_query(table_rows_query, printresults=False)
                    if table_rows_query_result_object['status']=='error':
                        print(table_rows_query_result_object)
                        print_plugin_debug(self.name, f"Error obtaining Schema for Table {table_name}. Table not supported or other error") 
                    else:
                        table_rows_query_results=table_rows_query_result_object['result']
                        extended_prompt =f"Below you have the schema and some sample rows of the content of table {table_name} in Microsoft Sentinel.\n"
                        extended_prompt +='I need you to create an JSON object with the most important fields and its description, type and sample anonymized data. When producing the output anonymize all user names, emails , domains and Tenant Ids. Limit the number of fields to 12\n'
                        extended_prompt +='Only Return a JSON object that follows this schema {"tableDescription":"This is the description of the Table","schemaDetails":[{"fieldName":"FieldName1","fieldType":"string","description":"This is the description of FieldName1","sampleValue":"This is an anonymized sample Value for fieldName1"},{"fieldName":"FieldName2","fieldType":"dynamic","description":"This is the description of FieldName2","sampleValue":"This is an anonymized sample Value for fieldName2"}]}\n'
                        extended_prompt +=f"This is the table Schema:\n {current_table_schema}\n" 
                        extended_prompt +=f"This is the sample data rows:\n {table_rows_query_results}\n"  
                        extended_schema = self.runpromptonAzureAI(extended_prompt,[])['result'].replace("```json", "").replace("```", "").strip()    
                        obj = json.loads(extended_schema) 
                        current_consolidated_schema[table_name]=obj
                        workspace_schema[table_name]=obj
                except Exception as err:
                    #raise(err)
                    print_plugin_debug(self.name, f"Error obtaining Schema for Table {table_name}. Table not supported")  
        #Save to workspace file for future runs. 
        with open(current_workspace_name+'.json', 'w+', encoding='utf-8') as f:  
            json.dump(workspace_schema, f, ensure_ascii=False, indent=4) 
        return current_consolidated_schema
    def loadSentinelSchema(self):  
        """  
        Load the Sentinel schema from a JSON file, generating it if it doesn't exist.  
  
        :return: Loaded Sentinel schema  
        """  
        print_plugin_debug(self.name, "Updating and Loading Sentinel Schema for current Workspace")  
        return self.generateSentinelSchema()

    def runKQLQuery(self, query, session,channel):  
        """  
        Generate a KQL query from a prompt and run it.  
  
        :param prompt: Input prompt  
        :param session: Session context  
        :return: Result of the KQL query  
        """
        query_results_object=self.sentinelClient.run_query(query, printresults=False)
        if query_results_object['status']=='error':
            channel('systemmessage',{"message":f"Error Running KQL: Trying to fix it"})
            print_plugin_debug(self.name, f"Error Running KQL: Trying to fix it")  
            new_query=self.fixKQLQuery(query, query_results_object['result'],[],channel)
            query_results_object=self.sentinelClient.run_query(new_query['result'], printresults=False)
        query_results_object["session_tokens"]=0   
        return  query_results_object 
    
    def generateNewKQL(self, prompt, session,channel):  
        """  
        Generate a KQL query from a prompt and run it.  
  
        :param prompt: Input prompt  
        :param session: Session context  
        :return: Result of the KQL query  
        """  
        extended_prompt = (  
            f"{prompt}\n"
            "- Only When asked to provide the most recent entry for Security Alerts or Security Incidents you can use | summarize arg_max(TimeGenerated, *) by <ID Field>. Place this summarize command in the first line of the query right after the table name\n"   
            "- The generated query must limit the number of output fields using project statement. Use project kql command to select the 6 or 7 most relevant fields based on the user request.\n" 
            "- If the user doesn't especify a number of desired results limit the results to 50 lines. Use |take 50 command.\n "
            "- Make sure the KQL query does not contains any empty lines as this breaks the KQL code.\n "
            "- Your response must only contain the KQL code. No additional code must be added before or after the KQL code.\n "  
            "- Remember that this prompt is part of a session with previous prompts and responses; therefore, you can use information from previous responses in the session if the prompt makes reference to previous results or data above.\n"  
            "- You can only use the fields detailed in the provided table schema.\n" 
        )
        return self.generateKQL(extended_prompt, session,channel)
    def extractKQL(self, prompt, session,channel):  
        """  
        extract a KQL query from a prompt and session.  
  
        :param prompt: Input prompt  
        :param session: Session context  
        :return: Result of the KQL query  
        """  
        extended_prompt = (  
            "You need to extract the KQL following these instructions and the prompt below.\n"   
            "- Make sure the KQL query does not contains any empty lines as this breaks the KQL code.\n "
            "- Your response must only contain the KQL code. No additional code must be added before or after the KQL code.\n "  
            "- Remember that this prompt is part of a session with previous prompts and responses; therefore, you can use information from previous responses in the session if the prompt makes reference to previous results or data above.\n"  
            "This is the user prompt:\n"
            f"{prompt}\n"
        )
        return self.generateKQL(extended_prompt, session,channel)
    def fixKQLQuery(self, query, error,session,channel):  
        extended_prompt = (  
        "I have run  the KQL query below in Microsoft Sentinel and I have received the error below as a result. I need you to fix the KQL query considering the provided error.\n" 
        "Make sure the KQL query follows KQL syntax.\n "
        "Make sure the KQL query does not contains any empty lines as this breaks the KQL code.\n "
        "Your response must only contain the KQL code. No additional code or text must be added before or after the KQL code.\n "
        "- Original KQL Query:\n" 
        f"{query}\n"
        "- Received Error:\n"  
        f"{error}\n"
        )
        return self.generateKQL(extended_prompt, session,channel)
    def generateKQL(self, extended_prompt, session,channel):  
        """  
        Generate a KQL query from a prompt and run it.  
  
        :param prompt: Input prompt  
        :param session: Session context  
        :return: Result of the KQL query  
        """  
        prompt_result_object = self.runpromptonAzureAI(extended_prompt, session) 
        if prompt_result_object['status']=='error':
            channel('systemmessage',{"message":f"Error (Generating KQL): {prompt_result_object['result'] }"})
            return prompt_result_object
        else:
        # Clean KQL tags from the result  
            query = prompt_result_object['result'].replace("```kql", "").replace("```kusto", "").replace("```", "").strip()
            channel('debugmessage',{"message":f"Generated KQL Query:\n {query}"})
            result_object={"status":prompt_result_object['status'],"result":query,"session_tokens":prompt_result_object['session_tokens']} 
            return  result_object
    
    def generateKQLWithSchemaAndTable(self, prompt, table, session,channel):  
        """  
        Generate a KQL query using the schema for a specific table and run it.  
  
        :param prompt: Input prompt  
        :param table: Table name  
        :param session: Session context  
        :return: Result of the KQL query  
        """  
        try:  
            extended_prompt = (  
                f"{prompt}\n"
                "Always Follow this instructions to generate the requested KQL query:\n"
                f"- You have to use the table {table} and only use fields included the following table schema (in JSON format): \n"  
                f"{self.sentinel_schema[table]['schemaDetails']} \n"
            )  
        except KeyError:  
            print_plugin_debug(self.name, f"Table '{table}' not found in schema. Generating Query without schema")  
            extended_prompt = prompt  
          
        query_object= self.generateNewKQL(extended_prompt, session,channel)  
        return query_object
  
    def findTable(self, prompt, session,channel):  
        """  
        Identify the best table to use for a given prompt.  
  
        :param prompt: Input prompt  
        :param session: Session context  
        :return: Best table name  
        """  
        table_list = ', '.join(self.sentinel_schema.keys())
        tableList=''
        for tableName in self.sentinel_schema.keys():
            tableList=tableList+tableName+': '+ self.sentinel_schema[tableName]['tableDescription'] +'\n'
        extended_prompt = (  
            f"This is the list of available tables and their description in my Sentinel instance: \n" 
            f"{tableList}\n" 
            "I need you to select the best available table to fulfill the prompt below:\n"  
            f"Prompt (Do not run): {prompt}\n"  
            "Make sure you ONLY respond with the name of the table avoiding any other text or character.\n"  
        ) 
        table = self.runpromptonAzureAI(extended_prompt, session)['result']  
        #print_plugin_debug(self.name, f"Selected Table: {table}")  
        return table  
  
    def runpromptonAzureAI(self, prompt, session):  
        """  
        Run a given prompt on the Azure OpenAI client.  
  
        :param prompt: Input prompt  
        :param session: Session context  
        :return: Response from Azure OpenAI Client  
        """
        result_object= self.azureOpenAIClient.runPrompt(prompt, session)
        return result_object
  
    def generateQuery(self, prompt, session,channel):  
        """  
        Convenience method to run the prompt and generate a KQL query with or without schema based on the plugin configuration.  
        :param prompt: Input prompt  
        :param session: Session context  
        :return: Result of the KQL query  
        """ 
        query_object={}
        if self.loadSchema:
            table = self.findTable(prompt, session,channel)  
            query_object= self.generateKQLWithSchemaAndTable(prompt, table, session,channel)
        else: 
            query_object= self.generateNewKQL(prompt, session,channel)
        return query_object
    def runtask(self, task, session,channel):  
        """  
        Convenience method to run the tasks inside the plugin.  
        :param task: Input task  
        :param session: Session context  
        :return: Result of the task execution 
        """ 
        if task["capability_name"]=="generateandrunkql":
            query_object = self.generateQuery( task["task"], session,channel)
            return self.runKQLQuery(query_object["result"], session,channel)
        else:
            if task["capability_name"]=="onlygeneratekql":
                return self.generateQuery(task["task"], session,channel)
            else:
                if task["capability_name"]=="extractandrunkql":
                    query_object = self.extractKQL( task["task"], session,channel)
                    return self.runKQLQuery(query_object["result"], session,channel)
