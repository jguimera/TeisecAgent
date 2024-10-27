from app.plugins.TeisecAgentPlugin import TeisecAgentPlugin
class GPTPlugin(TeisecAgentPlugin):
    def __init__(self, name, description,plugintype,azureOpenAIClient):
        super().__init__(name, description,plugintype)
        self.azureOpenAIClient=azureOpenAIClient
    def runpromptonAzureAI(self,prompt,session):
        result_object=self.azureOpenAIClient.runPrompt(prompt,session)
        return result_object
    def runprompt(self,prompt,session,channel):
        return self.runpromptonAzureAI(prompt,session)
    def pluginhelp(self):
        return "If your prompt doens't match any other plugin checks it will be submited to the GPT model"
    def plugincapabilities(self):  
        """  
        Provide the plugin capabilities.  
  
        :return: plugin capabilities object  
        """  
        capabilities={'runprompt':"This capability allows run a prompt without retrieving any additional external data. This plugin should be use if the user prompt doesn't require any additional or external data. THe main usage is to summarize current data or to generate new data based on the current context."}
        return  capabilities
    def runtask(self, task, session,channel):  
        """  
        Convenience method to run the tasks inside the plugin.  
        :param task: Input task  
        :param session: Session context  
        :return: Result of the task execution 
        """
        return self.runpromptonAzureAI(task["task"],session)