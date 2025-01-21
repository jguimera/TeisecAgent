from app.HelperFunctions import * 
class TeisecAgentPlugin:
    def __init__(self, name, description,plugintype):
        self.name = name
        self.description = name
        self.type = plugintype
        print_plugin_debug(self.name,f" Loading Copilot Plugin: {self.name}")
    def printname(self):
        print(self.name)
    def getname(self):
        return self.name
    def runtask(self,task,session):
        result_object={"status":"success","result":"","session_tokens":[{"scope":"plugin","session_tokens":22}],"prompt":task["task"]}
        print(self.task)
        return result_object
    def plugincapabilities(self):  
        capabilities={'plugincapabilitiy': {
                "description":"This capability allows for."}
        }
        return  capabilities