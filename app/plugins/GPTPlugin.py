from app.plugins.TeisecAgentPlugin import TeisecAgentPlugin
class GPTPlugin(TeisecAgentPlugin):
    def __init__(self, name, description,plugintype,azureOpenAIClient):
        super().__init__(name, description,plugintype)
        self.azureOpenAIClient=azureOpenAIClient
    def runpromptonAzureAI(self,prompt,session,scope='GPTPlugin'):
        result_object=self.azureOpenAIClient.runPrompt(prompt,session,scope)
        return result_object
    def plugincapabilities(self):  
        """  
        Provide the plugin capabilities.  
  
        :return: plugin capabilities object  
        """  
        capabilities={'runprompt':{
                "description":"This capability allows run a prompt without retrieving any additional external data. This plugin should be use if the user prompt doesn't require any additional or external data. THe main usage is to summarize current data or to generate new data based on the current context."}  
        } 
        return  capabilities
    def runtask(self, task, session,channel,parameters_object=[],scope='GPTPlugin'):  
        """  
        Convenience method to run the tasks inside the plugin.  
        :param task: Input task  
        :param session: Session context  
        :return: Result of the task execution 
        """
        result_object=self.runpromptonAzureAI(task["task"],session,scope='GPTPlugin')
        result_object["prompt"]=task["task"]
        return result_object