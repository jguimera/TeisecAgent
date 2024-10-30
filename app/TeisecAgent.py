import os  
from azure.identity import InteractiveBrowserCredential, ClientSecretCredential, DefaultAzureCredential  
from app.clients.SentinelClient import SentinelClient  
from app.clients.AzureOpenAIClient import AzureOpenAIClient  
from app.plugins.SentinelKQLPlugin import SentinelKQLPlugin  
from app.plugins.GPTPlugin import GPTPlugin  
from app.plugins.FetchURLPlugin import FetchURLPlugin  
from colorama import Fore  
from app.HelperFunctions import *  
import json 
import time  
class TeisecAgent:  
    def __init__(self, auth_type):  
        self.client_list = {}  
        self.plugin_list = {} 
        self.plugin_capabilities={}
        self.session = []  
        self.context_window_size = int(os.getenv('ASSISTANT_CONTEXT_WINDOW_SIZE', 5))  
        self.print_intro_message()  
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
        api_key = os.getenv('AZURE_OPENAI_APIKEY')  
        model_name = os.getenv('AZURE_OPENAI_MODELNAME')  
          
        self.client_list["azure_openai_client"] = AzureOpenAIClient(api_key, azure_endpoint, model_name)  
  
    def load_plugins(self):  
        """  
        Load plugins for the assistant. Currently hardcoded, but can be extended to auto-load from the plugins folder.  
        """  
        # TODO: Auto-load from all plugins available inside the plugins subfolder  
        loadSchema=(os.getenv('SENTINELKQL_LOADSCHEMA', 'True')=='True' )
        self.plugin_list = {  
            "SentinelKQLPlugin": SentinelKQLPlugin(  
                "SentinelKQLPlugin", "Plugin to generate and run KQL queries in Sentinel", "API",   
                self.client_list["azure_openai_client"], self.client_list["sentinel_client"],loadSchema
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
        self.plugin_capabilities={}
        for plugin_name in self.plugin_list.keys():
            plugincapability=self.plugin_list[plugin_name].plugincapabilities()
            self.plugin_capabilities[plugin_name]= plugincapability
    def decompose_in_tasks(self, prompt, channel):  
        """  
        Select the appropriate plugin based on the input prompt.  
        """  
        # System message to guide the AI assistant on how to decompose the prompt into tasks
        system_message='''
            You are an AI assistant designed to process user prompts by utilizing one or more capabilities from the available plugins. You will receive both the user prompt and the session's previous messages. Your task is to select the most appropriate plugins and capabilities to fulfill the user's request.
            Evaluate whether the user's prompt can be addressed by a single capability or if it needs to be broken down into multiple sequential tasks. When decomposing the prompt, remember that each task will have access to the results of the previous tasks as context, but not the original prompt.
            Ensure each task description includes all necessary details to achieve the expected results. Always return the output as an array, even if it contains only one task. The output must be in JSON format, adhering to the following schema:
            [  
                {  
                    "plugin_name": "<selected_plugin_name>",  
                    "capability_name": "<selected_capability_name>",  
                    "task": "<Task detailed description>"  
                }  
            ]  
            Below is the list of available plugins and their capabilities, which you will use to decompose the user's prompt into tasks:

            '''
        system_message=system_message+f'{self.plugin_capabilities}'
        # User prompt to be decomposed into tasks
        extended_user_prompt = (
            'Decompose the user prompt below in one or multiple tasks:\n'
            f'{prompt}'
            )
        
        # Create a new session with the system message and the current session
        system_object = {"role": "system", "content": system_message}
        new_session = []
        new_session.append(system_object)
        new_session = new_session + self.session
        
        # Run the prompt through the GPTPlugin to get the task list
        task_list_object = self.plugin_list["GPTPlugin"].runprompt(extended_user_prompt, new_session, channel)
        channel('debugmessage', {"message": f"Session Tokens (plugin selection): {task_list_object['session_tokens'] }"})  
        
        # Handle errors in the task list generation
        if task_list_object['status'] == 'error':
            channel('systemmessage', {"message": f"Error: {task_list_object['result'] }"})
            return []   
        else:
            # Clean tags from the result
            selected_plugin_string_clean = task_list_object['result'].replace("```plaintext", "").replace("```json", "").replace("```html", "").replace("```", "")  
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
    def get_plugin_help(self):  
        """  
        Get the plugin help information.  
        """
        plugin_help_list=[]  
        for plugin_name in self.plugin_list.keys():  
            plugin = self.plugin_list[plugin_name]  
            plugin_help = plugin.pluginhelp()
            plugin_help_list.append(plugin_help) 
        return plugin_help_list 
    def print_intro_message(self):  
        """  
        Print the introductory message for the assistant.  
        """  
        message = """

╔╦╗╔═╗╦╔═╗╔═╗╔═╗  ╔═╗╔═╗╔═╗╔╗╔╔╦╗
 ║ ║╣ ║╚═╗║╣ ║    ╠═╣║ ╦║╣ ║║║ ║ 
 ╩ ╚═╝╩╚═╝╚═╝╚═╝  ╩ ╩╚═╝╚═╝╝╚╝ ╩ 
                                                                         
            """ 
        print(f"{Fore.GREEN}{message}{Fore.WHITE}")  
        print_info("Welcome to Teisec Agent")  
  
    def process_response(self, output_type, user_input, response,channel):  
        """  
        Process the response to format it for specific output types (Terminal, HTML, etc.).  
        """  
        if output_type == 'terminal':  
            extended_prompt = (  
                'Below you have a prompt and the response associated with it. '  
                'Based on the prompt I need you to format the provided response to be shown in a terminal console. '  
                'If the response is a JSON object format it in a table for the terminal output unless specified otherwise below. '  
                'Make sure that the output table fits the screen. If a field takes more than 40 characters you should truncate it.\n'
                'Make sure you remove any reference to BlueVoyant or BV from the results. You can replace it with the text SEN.\n'   
                f'This is the original prompt (only use it to format the output): {user_input}\n'  
                f'This is the original prompt response (this is the data you have to format): \n{response}'  
            )  
        elif output_type == 'html':  
            extended_prompt = (  
                'Below you have a prompt and the response associated with it. '  
                'Based on the original prompt I need you to format the provided response to be shown in a browser in HTML format. Your response will be embedded inside a chat session.'  
                'You do not need to include the whole HTML document, only a div element with the results. No style is needed.'
                'If the original prompt is asking to only generate a code, either JSON, KQL or YAML please wrap the code in iside a code block like this: <div class="relative bg-gray-100 rounded-lg dark:bg-gray-100 p-4"><div class="max-h-full"><pre><code id="code-block" class="text-sm text-black-500 dark:text-black-500 whitespace-pre"> Returned Code </code></pre></div></div>'
                'If the original prompt is asking to retrieve some data and the response is a JSON object, you must format it in a table for the HTML output. '  
                'Make sure that the output html table is responsive. If a field takes more than 40 characters you can truncate it.\n'  
                f'This is the original prompt (only use it to format the output): {user_input}\n'  
                f'This is the original prompt response (this is the data you have to format): \n{response}'  
            )  
        elif output_type == 'other':  
            extended_prompt = (  
                'Below you have a prompt and the response associated with it. '  
                'Based on the prompt I need you to format the provided response to be shown using plain text format. '  
                'If the response is a JSON object format it in a table for the plain text output. '  
                'Make sure that the output html table is responsive. If a field takes more than 40 characters you can truncate it.\n'  
                f'This is the original prompt (only use it to format the output): {user_input}\n'  
                f'This is the original prompt response (this is the data you have to format): \n{response}'  
            )  
  
        prompt_result_object = self.plugin_list["GPTPlugin"].runprompt(extended_prompt, [],channel)  
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
    def run_prompt(self, output_type, prompt,channel=None):  
        """  
        Run the provided prompt using task decomposition.  
        """  
        start_time = time.time()  
        task_results=[]
        decomposed_tasks=self.decompose_in_tasks(prompt,channel)
        self.send_system(channel,{"message":'Prompt decomposed in '+ str(len(decomposed_tasks))+' tasks'})
        for task in decomposed_tasks:
            self.send_system(channel,{"message":'('+task['plugin_name']+') '+task['task']})
            plugin_response_object = self.get_plugin(task['plugin_name']).runtask(task, self.session,channel)  
            if plugin_response_object['status']=='error':
                channel('systemmessage',{"message":f"Error: {plugin_response_object['result'] }"})
                break   
            else:
                self.update_session(prompt, plugin_response_object['result'])
                processed_response = self.process_response(output_type, prompt, str(plugin_response_object['result']),channel)
                task_results.append(processed_response)  
                self.send_response(channel,{"message":processed_response})     
                self.send_debug(channel,{"message":f"Session Lenght: {len(self.session)}"})  
        # Stop the timer  
        end_time = time.time()  
        # Calculate the elapsed time  
        elapsed_time = round(end_time - start_time )
        self.send_system(channel,{"message":f"Processing Time: {elapsed_time} seconds"}) 
        return task_results
  
    def update_session(self, prompt, plugin_response):  
        """  
        Update the session with the latest prompt and response.  
        """  
        user_object = {"role": "user", "content": [{"type": "text", "text": prompt}]}  
        assistant_object = {"role": "assistant", "content": [{"type": "text", "text": str(plugin_response)}]}  
  
        if len(self.session) >= self.context_window_size * 2:  
            self.session.pop(0)  # Remove the oldest element twice (Assistant and User)  
            self.session.pop(0)  
  
        self.session.append(user_object)  
        self.session.append(assistant_object)  
  
    def clear_session(self):  
        """  
        Clear the current session.  
        """  
        print_info("Session Cleared")  
        self.session.clear()  
