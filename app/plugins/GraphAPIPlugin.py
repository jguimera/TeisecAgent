from app.plugins.TeisecAgentPlugin import TeisecAgentPlugin  
from colorama import Fore  
import json  
import os  
from app.HelperFunctions import print_plugin_debug  
  
class GraphAPIPlugin(TeisecAgentPlugin):  
    """  
    Plugin to generate and run KQL queries adhering to the Sentinel schema.  
    """  
  
    def __init__(self, name, description, plugintype, azureOpenAIClient, graphAPIClient):  
        """  
        Initialize the GraphAPIKQLPlugin.  
  
        :param name: Name of the plugin  
        :param description: Description of the plugin  
        :param plugintype: Type of the plugin  
        :param azureOpenAIClient: Azure OpenAI Client instance  
        :param graphAPIClient: GraphAPI Client instance  
        """  
        super().__init__(name, description, plugintype)  
        self.azureOpenAIClient = azureOpenAIClient  
        self.graphAPIClient = graphAPIClient  
  
    def plugincapabilities(self):  
        """  
        Provide the plugin capabilities.  
  
        :return: plugin capabilities object  
        """  
        capabilities={
            "getemaildetails":"This capability allows to retrieve and analyze the body and headers of an specific  email sent or received in my organization. Don't use this skill to list or retrieve multiple emails. If available include the mailbox address and InternetMessageId in the task description. If not available this capability will look for them in the previous messages. To select the correct mailbox please consider the EmailDirection field, inbound=Recipient outbound=Sender" }
        return  capabilities
    def runpromptonAzureAI(self, prompt, session):  
        """  
        Run a given prompt on the Azure OpenAI client.  
  
        :param prompt: Input prompt  
        :param session: Session context  
        :return: Response from Azure OpenAI Client  
        """
        result_object= self.azureOpenAIClient.runPrompt(prompt, session)
        return result_object
    def extract_capability_parameters(self, input_parameters, prompt, session, channel):
        """  
        Extract and replace the input parameters of the plugin from the user prompt and the current session.  
        """  
        extended_prompt = (
            '''You need to extract the input parameters for the plugin from the prompt below or the previous messages in the session.
            Always return the output as an object. The output must be in JSON format, adhering to the following schema:
            {
                "parameters_found": "yes or no (if the parameters were found in the prompt or the session context)",
                "parameters": {
                    "parameter_name_1": "parameter_value_1",
                    "parameter_name_2": "parameter_value_2",
                    ...
                }
            }
            Don't add any other text to the response, only the JSON object.
            '''
            f"These are the parameters required for the workflow: {input_parameters}\n"
            f"The following user prompt gives you the instructions to fill the values of the parameter object. The values might be inside the prompt itself or inside the previous messages in the session context (Do not run):\n {prompt}\n"
        )
        print_plugin_debug(self.name, f"Running prompt to extract parameters: {extended_prompt}")
        parameters = self.runpromptonAzureAI(extended_prompt, session)['result']  
        paremeters_clean=parameters.replace("```plaintext", "").replace("```json", "").replace("```html", "").replace("```", "")  
        print_plugin_debug(self.name, f"Extracted parameters: {paremeters_clean}")  
        try:
            # Parse the cleaned result into a JSON object
            obj = json.loads(paremeters_clean)
            return obj
        except:
            # Handle JSON parsing errors
            channel('systemmessage', {"message": f"Error: {'Error generating parameters.'}"})
            obj = {}
            return obj
    def getEmailDetails(self, parametersObject, session,channel):  
        """  
        Convenience method to run the prompt and retrieve the Email details.  
        :param parametersObject: Input Parameters details  
        :param session: Session context  
        :return: Details of the email 
        """ 
        mailbox=parametersObject['mailbox']
        internetmessageid=parametersObject['internetmessageid']
        emailDetails_object=self.graphAPIClient.get_email(mailbox,internetmessageid)
        if emailDetails_object['status']=='error':
            channel('systemmessage',{"message":f"Error obtaining Email: {emailDetails_object["result"]}"})
            print_plugin_debug(self.name, f"Error obtaining Email: {emailDetails_object["result"]}")   
            #result_object={"status":"error","result":emailDetails_object["result"],"session_tokens":0}
        #result_object={"status":"sucess","result":emailDetails_object["result"],"session_tokens":0} 
        return emailDetails_object
    def runtask(self, task, session,channel):  
        """  
        Convenience method to run the tasks inside the plugin.  
        :param task: Input task  
        :param session: Session context  
        :return: Result of the task execution 
        """ 
        if task["capability_name"]=="getemaildetails":
            #parameters_object = self.extractParameters( task["task"], session,channel)
            input_parameters={
                    "mailbox": "<user mailbox address to extract the email from>",  
                    "internetmessageid": "<Email Internet Message Id>"
                }  
            print(session)
            parameters_object = self.extract_capability_parameters(input_parameters,task["task"] , session,channel)
            if parameters_object['parameters_found']=="yes":    
                return self.getEmailDetails(parameters_object["parameters"], session,channel)
            else:
                result_object={"status":"error","result":"Parameters not found","session_tokens":0} 
                return result_object
        else:
            result_object={"status":"error","result":"Capability not found","session_tokens":0} 
            return result_object
