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
        self.schema_file = 'SentinelSchema.json'  
        self.extended_schema_file = 'extended_schema.json'
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
            "generateandrunkql":"This capability allows to generate and run one KQL query to retrieve logs and events from Microsoft Sentinel. This capability should be used when the user ask about retrieving new incidents or alerts. Other type of common data is Signin and Audit logs. Do not use this capabilitiy if the user ask for only KQL generation without runing it"
            ,"onlygeneratekql":"This capability allows to generate one KQL query for Microsoft Sentinel without runing the query. This capability should be used when the user ask about only generating a query for Sentinel without running it."
            }
        return  capabilities
  
    def generateSentinelSchema(self):  
        """  
        Retrieve and store the schema of Azure Sentinel tables.  
        """  
        query = "Usage | summarize by DataType"  
        query_results = self.sentinelClient.run_query(query, printresults=False)  
        table_schemas = {}  
        table_extended_schemas = {} 
        print_plugin_debug(self.name, f"Retrieving Sentinel Schema for Workspace tables ({len(query_results)})")  
        for table in query_results:  
            table_name=table['DataType']
            table_schema = f"{table_name} | getschema kind=csl"
            try:
                table_schema_results = self.sentinelClient.run_query(table_schema, printresults=False)
                table_schemas[table_name] = table_schema_results[0]['Schema']  
                table_rows_query = f"{table_name} | where TimeGenerated > ago(30d) |take 3"  
                table_rows_query_results = self.sentinelClient.run_query(table_rows_query, printresults=False)   
                extended_prompt =f"Below you have the schema and some sample rows of the content of table {table_name} in Microsoft Sentinel.\n"
                if table_name in ['SecurityAlert','SecurityIncident']:
                    extended_prompt +="I need you to create an JSON object with all the fields and its description.\n"
                else: 
                   extended_prompt +='I need you to create an JSON object with the most important fields and its description.Limit the number of fields to 12\n'
                extended_prompt +='Only Return a JSON object that follows this schema {"tableDescription":"This is the description of the Table","schemaDetails":[{"fieldName":"FieldName1","fieldType":"string","description":"This is the description of FieldName1","sampleValue":"This is a sample Value for fieldName1"},{"fieldName":"FieldName2","fieldType":"dynamic","description":"This is the description of FieldName2","sampleValue":"This is a sample Value for fieldName2"}]}\n'
                extended_prompt +=f"This is the table Schema:\n {table_schemas[table_name]}\n" 
                extended_prompt +=f"This is the sample data rows:\n {table_rows_query_results}\n"  
                extended_schema = self.runpromptonAzureAI(extended_prompt,[])['result'].replace("```json", "").replace("```", "").strip()    
                obj = json.loads(extended_schema) 
                table_extended_schemas[table_name]=obj
            except Exception as err:
                print_plugin_debug(self.name, f"Error obtaining Schema for Table {table_name}. Table not supported")  
        with open(self.schema_file, 'w', encoding='utf-8') as f:  
            json.dump(table_schemas, f, ensure_ascii=False, indent=4) 
        with open('extended_schema.json', 'w', encoding='utf-8') as f:  
            json.dump(table_extended_schemas, f, ensure_ascii=False, indent=4) 
  
    def loadSentinelSchema(self):  
        """  
        Load the Sentinel schema from a JSON file, generating it if it doesn't exist.  
  
        :return: Loaded Sentinel schema  
        """  
        print_plugin_debug(self.name, "Loading Sentinel Schema for Workspace")  
        if not os.path.isfile(self.extended_schema_file):  
            self.generateSentinelSchema()  
          
        with open(self.extended_schema_file, 'r', encoding='utf-8') as f:  
            return json.load(f)  
    def runKQLQuery(self, query, session,channel):  
        """  
        Generate a KQL query from a prompt and run it.  
  
        :param prompt: Input prompt  
        :param session: Session context  
        :return: Result of the KQL query  
        """ 
        query_results=self.sentinelClient.run_query(query, printresults=False)
        result_object={"status":"success","result":query_results,"session_tokens":0}   
        return  result_object 
    def generateKQL(self, prompt, session,channel):  
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
            "- Limit the results to 100 lines. Use |take 100 command.\n "
            "- Your response must only contain the KQL code. No additional code must be added before or after the KQL code.\n "  
            "- Remember that this prompt is part of a session with previous prompts and responses; therefore, you can use information from previous responses in the session if the prompt makes reference to previous results or data above.\n"  
        )
        prompt_result_object = self.runpromptonAzureAI(extended_prompt, session) 
        if prompt_result_object['status']=='error':
            channel('systemmessage',{"message":f"Error (Generating KQL): {prompt_result_object['result'] }"})
            return prompt_result_object
        else:
        # Clean KQL tags from the result  
            query = prompt_result_object['result'].replace("```kql", "").replace("```kusto", "").replace("```", "").strip()  
            print_plugin_debug(self.name, f"Generated Query:\n {query}")  
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
                f"- Make sure you use the {table} table and use only fields defined the following schema (in JSON format): \n"  
                f"{self.sentinel_schema[table]["schemaDetails"]} \n"
            )  
        except KeyError:  
            print_plugin_debug(self.name, f"Table '{table}' not found in schema. Generating Query without schema")  
            extended_prompt = prompt  
          
        query_object= self.generateKQL(extended_prompt, session,channel)  
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
        print_plugin_debug(self.name, f"Selected Table: {table}")  
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
            query_object= self.generateKQL(prompt, session,channel)
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
