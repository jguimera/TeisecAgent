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
    def extractParameters(self, prompt, session,channel):  
        """  
        Extract the necessary parameters for the GraphAPI request.  
  
        :param prompt: Input prompt  
        :param session: Session context  
        :return: parameters object  
        """  
        extended_prompt_get_emails = (  
            '''You need to extract either from the prompt below or the previous messages in the session a set of parameters to be used by other methods in this agentic system.
                Always return the output as an object. The output must be in JSON format, adhering to the following schema: 
                {  
                    "parameters_found":"yes or no (if the parameters were found in the prompt or the session context)",
                    "mailbox": "<user mailbox address to extract the email from>",  
                    "internetmessageid": "<Email Internet Message Id>"
                }  
            ]
            Don't add any other text to the response, only the JSON object.
            ''' 
            f"This is the Prompt from where you can extract some of the required details to produce the requested output (Do not run):\n {prompt}\n"   
        ) 

        parameters = self.runpromptonAzureAI(extended_prompt_get_emails, session)['result']  
        paremeters_clean=parameters.replace("```plaintext", "").replace("```json", "").replace("```html", "").replace("```", "")  
        print_plugin_debug(self.name, f"Extracted parameters: {paremeters_clean}")  
        try:
            # Parse the cleaned result into a JSON object
            obj = json.loads(paremeters_clean) 
            return obj
        except:
            # Handle JSON parsing errors by defaulting to using the GPTPlugin
            channel('systemmessage', {"message": f"Error: {'Error generating parameters.'}"})
            obj = {}
            #TODO Generate Error message
            return obj
  

  
    def getEmailDetails(self, parametersObject, session,channel):  
        """  
        Convenience method to run the prompt and retrieve the Email details.  
        :param parametersObject: Input Parameters details  
        :param session: Session context  
        :return: Details of the email 
        """ 
        #TODO Check the correctness of parameters
        mailbox=parametersObject['mailbox']
        internetmessageid=parametersObject['internetmessageid']
        #TODO Check for errors in the response and create the right object
        emailDetails=self.graphAPIClient.get_email(mailbox,internetmessageid)
        result_object={"status":"sucess","result":emailDetails,"session_tokens":0} 
        return result_object
    def runtask(self, task, session,channel):  
        """  
        Convenience method to run the tasks inside the plugin.  
        :param task: Input task  
        :param session: Session context  
        :return: Result of the task execution 
        """ 
        if task["capability_name"]=="getemaildetails":
            parameters_object = self.extractParameters( task["task"], session,channel)
            if parameters_object['parameters_found']=="yes":    
                return self.getEmailDetails(parameters_object, session,channel)
            else:
                result_object={"status":"error","result":"Parameters not found","session_tokens":0} 
                return result_object
        else:
            result_object={"status":"error","result":"Capability not found","session_tokens":0} 
            return result_object
