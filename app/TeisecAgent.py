import os  
from azure.identity import InteractiveBrowserCredential, ClientSecretCredential, DefaultAzureCredential  
from app.clients.SentinelClient import SentinelClient  
from app.clients.AzureOpenAIClient import AzureOpenAIClient  
from app.clients.GraphAPIClient import GraphAPIClient 
from app.plugins.GraphAPIPlugin import GraphAPIPlugin  
from app.plugins.SentinelKQLPlugin import SentinelKQLPlugin  
from app.plugins.GPTPlugin import GPTPlugin  
from app.plugins.FetchURLPlugin import FetchURLPlugin  
from colorama import Fore  
from app.HelperFunctions import *  
from app.Prompts import TeisecPrompts
import json 
import time  
import string
import concurrent
from concurrent.futures import ThreadPoolExecutor

class TeisecAgent:  
    def __init__(self, auth_type):  
        self.client_list = {}  
        self.plugin_list = {} 
        self.plugin_capabilities={}
        self.session = [{"role":"system","content":TeisecPrompts["Core.Main.System"]}]  
        self.context_window_size = int(os.getenv('ASSISTANT_CONTEXT_WINDOW_SIZE', 5))  
        print_intro_message()  
        if auth_type!=None:
            self.auth(auth_type)  
            self.create_clients()  
            self.load_plugins()  
            self.load_plugin_capabilities()
        self.workflow_list = {}
        self.load_workflows()
    def launch_auth(self,auth_type):
        self.auth(auth_type)  
        self.create_clients()  
        self.load_plugins()  
        self.load_plugin_capabilities()    
    def auth(self, auth_type):  
        """  
        Authenticate with Azure using different credential types based on the provided auth_type.  
        """  
        # Use different types of Azure Credentials based on the argument  
        if auth_type == "interactive":  
            self.credential = InteractiveBrowserCredential()  
        elif auth_type == "client_secret":  
            self.credential = ClientSecretCredential(  
                tenant_id=os.getenv('AZURE_TENANT_ID'),  
                client_id=os.getenv('AZURE_CLIENT_ID'),  
                client_secret=os.getenv('AZURE_CLIENT_SECRET')  
            )  
        else:  
            # Managed Identity to be used when running in Azure Serverless functions.  
            self.credential = DefaultAzureCredential()  
        # Force authentication to make the user login  
        print_info("Authenticating with Azure...")  
        try:  
            self.credential.get_token("https://management.azure.com/.default")  
            print_info("Authentication successful")  
        except Exception as e:  
            print_error(f"Authentication failed: {e}")  
            print_error("Only unauthenticated plugins can be used")  
    def create_clients(self):  
        """  
        Create clients to external platforms using environment variables.  
        """  
        subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID')  
        resource_group_name = os.getenv('AZURE_RESOURCEGROUP_NAME')  
        workspace_name = os.getenv('AZURE_WORKSPACE_NAME')  
        workspace_id = os.getenv('AZURE_WORKSPACE_ID')  
          
        self.client_list["sentinel_client"] = SentinelClient(  
            self.credential, subscription_id, resource_group_name, workspace_name, workspace_id  
        )  
        azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')  
        api_key = os.getenv('AZURE_OPENAI_API_KEY')  
        model_name = os.getenv('AZURE_OPENAI_MODELNAME')  
          
        self.client_list["azure_openai_client"] = AzureOpenAIClient(api_key, azure_endpoint, model_name)  
        #Requires Mail.Read Application Permission if used with Service Principal
        self.client_list["graph_api_client"] = GraphAPIClient(  
            self.credential) 
    def load_capabilities(self):
        """  
        Load custom capabilities from the capabilities folder.  
        """  
        capabilities_folder = os.path.join(os.getcwd(), 'capabilities')
        custom_capabilities = {}
        for filename in os.listdir(capabilities_folder):
            if filename.endswith('.json'):
                filepath = os.path.join(capabilities_folder, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    print_debug(f"Loading custom capabilities from {filename}")
                    capabilities = json.load(f)
                    for capability in capabilities['custom_capabilities']:
                        plugin_name = capability['plugin_name']
                        if (plugin_name not in custom_capabilities):
                            custom_capabilities[plugin_name] = []
                        custom_capabilities[plugin_name].append(capability)
        return custom_capabilities

    def load_plugins(self):  
        """  
        Load plugins for the assistant. Currently hardcoded, but can be extended to auto-load from the plugins folder.  
        """  
        # TODO: Auto-load from all plugins available inside the plugins subfolder  
        loadSchema=(os.getenv('SENTINELKQL_LOADSCHEMA', 'True')=='True' )
        custom_capabilities = self.load_capabilities()
        self.plugin_list = {  
            "GraphAPIPlugin":GraphAPIPlugin(  
                "GraphAPIPlugin", "Plugin to retrieve data from the Microsoft GraphAPI", "API", self.client_list["graph_api_client"]
            ),
            "SentinelKQLPlugin": SentinelKQLPlugin(  
                "SentinelKQLPlugin", "Plugin to generate and run KQL queries in Sentinel", "API",   
                self.client_list["azure_openai_client"], self.client_list["sentinel_client"], loadSchema, custom_capabilities.get("SentinelKQLPlugin", [])
            ),  
            "FetchURLPlugin": FetchURLPlugin(  
                "FetchURLPlugin", "Plugin to fetch HTML sites", "API",   
                self.client_list["azure_openai_client"]  
            ),  
            "GPTPlugin": GPTPlugin(  
                "GPTPlugin", "Plugin to run prompts in Azure OpenAI GPT models", "GPT",   
                self.client_list["azure_openai_client"]  
            )  
        }  
    def load_plugin_capabilities(self):
        self.plugin_capabilities=[]
        for plugin_name in self.plugin_list.keys():
            plugincapability=self.plugin_list[plugin_name].plugincapabilities()
            plugin={
                "plugin_name":plugin_name,
                "capabilities":plugincapability
            }
            self.plugin_capabilities.append(plugin)
    def load_workflows(self):
        """  
        Load workflows from the workflows folder.  
        """  
        workflows_folder = os.path.join(os.getcwd(), 'workflows')
        for filename in os.listdir(workflows_folder):
            if filename.endswith('.json'):
                filepath = os.path.join(workflows_folder, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                    self.workflow_list[workflow['workflow']['shortcut']] = workflow
    def get_workflow(self, shortcut):
        """  
        Get the workflow by its shortcut.  
        """  
        return self.workflow_list.get(shortcut, None)
    
    def replace_template_placeholders(self, template_name, **kwargs):
        """  
        Replace placeholders in the template with provided values.  
        """  
        template = string.Template(TeisecPrompts[template_name])
        return template.safe_substitute(**kwargs)

    def decompose_in_tasks(self, prompt, channel):  
        """  
        Select the appropriate plugin based on the input prompt.  
        """  
        # System message to guide the AI assistant on how to decompose the prompt into tasks
        system_message = self.replace_template_placeholders("Core.Decompose.System", AgentCapabilities=self.plugin_capabilities)
        
        # User prompt to be decomposed into tasks
        extended_user_prompt = self.replace_template_placeholders("Core.Decompose.User", UserPrompt=prompt)
        
        # Create a new session with the system message and the current session
        system_object = {"role": "system", "content": system_message}
        new_session = []
        new_session.append(system_object)

        new_session = new_session + self.session[1:]
        
        # Run the prompt through the GPTPlugin to get the task list
        task={}
        task["task"]=extended_user_prompt
        task_list_object = self.plugin_list["GPTPlugin"].runtask(task, new_session, channel, [],scope='Core-Decompose')
        channel('debugmessage', {"message": f"Session Tokens (plugin selection): {task_list_object['session_tokens'] }"})  
        
        # Handle errors in the task list generation
        if task_list_object['status'] == 'error':
            channel('systemmessage', {"message": f"Error: {task_list_object['result'] }"})
            return []   
        else:
            # Clean tags from the result
            selected_plugin_string_clean = task_list_object['result'].replace("```plaintext", "").replace("```json", "").replace("```html", "").replace("```", "")  
            #self.update_session(extended_user_prompt, selected_plugin_string_clean)
            try:
                # Parse the cleaned result into a JSON object
                obj = json.loads(selected_plugin_string_clean) 
                return obj
            except:
                # Handle JSON parsing errors by defaulting to using the GPTPlugin
                channel('systemmessage', {"message": f"Error: {'Error Decomposing. Running User Prompt with GPT Plugin' }"})
                obj = [{"plugin_name": "GPTPlugin", "capability_name": "runprompt", "task": prompt}]
                return obj
    def get_plugin(self, plugin_id):  
        """  
        Get the plugin instance by its ID.  
        """  
        return self.plugin_list[plugin_id]  
    def process_response(self, output_type, user_input, response,channel):  
        """  
        Process the response to format it for specific output types (Terminal, HTML, etc.).  
        """  
        if output_type == 'terminal':  
            extended_prompt = self.replace_template_placeholders("Core.Output.Terminal", UserInput=user_input, Response=response)  
        elif output_type == 'html':  
            extended_prompt = self.replace_template_placeholders("Core.Output.HTML", UserInput=user_input, Response=response)    
        elif output_type == 'other':  
            extended_prompt = self.replace_template_placeholders("Core.Output.Other", UserInput=user_input, Response=response)  
        task={}
        task["task"]=extended_prompt
        prompt_result_object = self.plugin_list["GPTPlugin"].runtask(task, [],channel, [],scope='Core-Output')  
        if prompt_result_object['status']=='error':
            channel('systemmessage',{"message":f"Error: {prompt_result_object['result'] }"})
            return  ''   
        else:
            # Clean tags from result  
            prompt_result_clean = prompt_result_object['result'].replace("```plaintext", "").replace("```kusto", "").replace("```html", "").replace("```", "")  
            return prompt_result_clean  
    def send_system (self,channel,system_object):
        if channel is not None:
            channel('systemmessage',system_object)
    def send_debug (self,channel,debug_object):
        if channel is not None:
            channel('debugmessage',debug_object)
    def send_response (self,channel,response_object):
        if channel is not None:
            channel('resultmessage',response_object)   
    def run_prompt(self, output_type, prompt, channel=None):  
        """  
        Run the provided prompt using task decomposition or workflow.  
        """  
        if prompt.startswith('/'):
            shortcut = prompt[1:].split(' ')[0]
            workflow = self.get_workflow(shortcut)
            if workflow:
                self.send_system(channel, {"message": f"Running workflow: {workflow['workflow']['title']}"} )
                return self.run_workflow(output_type, workflow, prompt, channel)
            else:
                self.send_system(channel, {"message": f"Workflow shortcut '{shortcut}' not found."})
                return []
        else:
            return self.decompose_and_run_prompt(output_type, prompt, channel)

    def run_task(self, task, channel=None):
        #get plugin and Capability
        plugin_name=task['plugin_name']
        try:
            plugin=self.get_plugin(plugin_name)
            capability=plugin.plugincapabilities()[task['capability_name']]
        except: 
            channel('systemmessage', {"message": f"Error: Plugin or Capability not found."})    
            return {"status": "error", "result": f"Error: Plugin or Capability not found."}
        
        #check if capabilitiy has input parameters
        parameters_object=None
        if 'parameters' in capability:
            #extract parameters
            parameters_object=self.extract_parameters(capability['parameters'],task['task'],self.session,channel)
        #run task
        plugin_response_object = plugin.runtask(task, self.session, channel,parameters_object)
        if plugin_response_object['status'] == 'error':
                channel('systemmessage', {"message": f"Error: {plugin_response_object['result'] }"})   
        else:
            self.update_session(task['task'], plugin_response_object['result'])
            self.send_debug(channel, {"message": f"Session Length: {len(self.session)}"})
        return plugin_response_object
    def decompose_and_run_prompt(self, output_type, prompt, channel=None):
        """  
        Run the provided prompt using task decomposition.  
        """  
        start_time = time.time()  
        task_results = []
        decomposed_tasks = self.decompose_in_tasks(prompt, channel)
        self.send_system(channel, {"message": 'Prompt decomposed in ' + str(len(decomposed_tasks)) + ' tasks'})
        for task in decomposed_tasks:
            self.send_system(channel, {"message": '(' + task['plugin_name'] + '-' + task['capability_name'] + ') ' + task['task']})
            plugin_response_object=self.run_task(task,channel)
            processed_response = self.process_response(output_type, task['task'], str(plugin_response_object['result']), channel)
            task_results.append(processed_response)  
            self.send_response(channel, {"message": processed_response})      
        # Stop the timer  
        end_time = time.time()  
        # Calculate the elapsed time  
        elapsed_time = round(end_time - start_time)
        self.send_system(channel, {"message": f"Processing Time: {elapsed_time} seconds"}) 
        return task_results

    def extract_parameters(self, parameters, prompt, session, channel):
        """  
        Extract and replace the input parameters from the user prompt and the current session.  
        """  
        extended_prompt = self.replace_template_placeholders("Core.ExtractParameters.System", UserInput=prompt, Parameters=parameters)  
        task={}
        task["task"]=extended_prompt
        parameters = self.plugin_list["GPTPlugin"].runtask(task, session, channel, [],scope='Core-ParametersExtraction')['result']
        parameters_clean = parameters.replace("```plaintext", "").replace("```json", "").replace("```html", "").replace("```", "")
        print_plugin_debug("TeisecAgent", f"Extracted parameters: {parameters_clean}")
        try:
            # Parse the cleaned result into a JSON object
            obj = json.loads(parameters_clean)
            return obj
        except:
            # Handle JSON parsing errors
            channel('systemmessage', {"message": f"Error: {'Error generating parameters.'}"})
            obj = {}
            return obj

    def run_workflow(self, output_type, workflow, prompt, channel=None):
        """  
        Run the provided workflow.  
        """  
        start_time = time.time()  
        task_results = []
        parameters_object = self.extract_parameters(workflow['workflow']['input_parameters'], prompt, self.session, channel)
        if parameters_object['parameters_found'] == "yes":
            for workflow_task in workflow['workflow']['tasks']:
                tasks_to_run=[]
                if 'parallel_tasks' in workflow_task:
                    tasks_to_run.extend(workflow_task['parallel_tasks'])
                else:
                    tasks_to_run.append(workflow_task)
                for task_to_run in tasks_to_run:
                    plugin_response_object=self.run_workflow_task( task_to_run,parameters_object, channel)
                    self.send_system(channel, {"message": '(' + task_to_run['plugin_id'] + '-' + task_to_run['capability_name'] + ') ' + plugin_response_object['prompt']})
                    if plugin_response_object['status'] == 'error':
                        channel('systemmessage', {"message": f"Error: {plugin_response_object['result'] }"})
                        break   
                    else:
                        self.update_session(plugin_response_object['prompt'], plugin_response_object['result'])
                        processed_response = self.process_response(output_type, plugin_response_object['prompt'], str(plugin_response_object['result']), channel)
                        task_results.append(processed_response)  
                        self.send_response(channel, {"message": processed_response})     
                        self.send_debug(channel, {"message": f"Session Length: {len(self.session)}"})  
        else:
            self.send_system(channel, {"message": "Error: Required parameters not found in the prompt or session."})
        # Stop the timer  
        end_time = time.time()  
        # Calculate the elapsed time  
        elapsed_time = round(end_time - start_time)
        self.send_system(channel, {"message": f"Processing Time: {elapsed_time} seconds"}) 
        return task_results
    def run_workflow_task(self, workflow_task,parameters_object, channel=None):
        task_prompt = workflow_task['prompt_text']
        for param_name, param_value in parameters_object['parameters'].items():
            task_prompt = task_prompt.replace(f"{{{{{param_name}}}}}", param_value)
        task = {
            "plugin_name": workflow_task['plugin_id'],
            "capability_name": workflow_task['capability_name'],
            "task": task_prompt
        }
        #self.send_system(channel, {"message": '(' + task['plugin_name'] + '-' + task['capability_name'] + ') ' + task['task']})
        plugin_response_object=self.run_task(task,channel) 
        return plugin_response_object       
    def run_parallel_workflow(self, output_type, workflow, prompt, channel=None):
        results = []  
        # Using ThreadPoolExecutor to process items in parallel  
        with concurrent.futures.ThreadPoolExecutor( max_workers=10) as executor:  
            # Map the processing function to the items and collect the results  
            for result in executor.map(runPromptonItem, UCList):  
                results.append(result)  
    def update_session(self, prompt, plugin_response):  
        """  
        Update the session with the latest prompt and response.  
        """  
        user_object = {"role": "user", "content": [{"type": "text", "text": prompt}]}  
        assistant_object = {"role": "assistant", "content": [{"type": "text", "text": str(plugin_response)}]}  
        if len(self.session) >= self.context_window_size * 2:  
            self.session.pop(1)  # Remove the oldest element twice (Assistant and User) . First Item is the System Message 
            self.session.pop(1)  
        self.session.append(user_object)  
        self.session.append(assistant_object)  
    def clear_session(self):  
        """  
        Clear the current session.  
        """  
        print_info("Session Cleared")  
        #self.session.clear()
        self.session = [{"role":"system","content":TeisecPrompts["Core.Main.System"]}]  
