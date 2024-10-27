# Teisec Agent Plugin System  
  
## Overview  
  
This Teisec Agent is designed with a plugin-based architecture, allowing it to extend its functionality through various plugins. Each plugin focuses on a specific task and can be easily added or modified. This document provides an overview of the existing plugins and guidelines for creating new ones.  
  
## Existing Plugins  
  
### TeisecAgentPlugin  
  
This is the base class for all plugins. It includes basic methods that can be overridden by derived classes.  
  
#### Methods  
- `__init__(self, name, description, plugintype)`: Initializes the plugin with a name, description, and type.  
- `printname(self)`: Prints the name of the plugin.  
- `getname(self)`: Returns the name of the plugin.  
- `runtask(self, task, session)`: Placeholder method to run a task.  
- `plugincapabilities(self)`: Provides the plugin capabilities.  
- `pluginhelp(self)`: Provides help instructions for the plugin.  
  
### GPTPlugin  
  
This plugin interacts with the Azure OpenAI Client to process prompts that do not match any other specific plugin.  
  
#### Methods  
- `__init__(self, name, description, plugintype, azureOpenAIClient)`: Initializes the plugin with additional Azure OpenAI Client.  
- `runpromptonAzureAI(self, prompt, session)`: Runs a given prompt on the Azure OpenAI Client.  
- `runtask(self, task, session, channel)`: Runs the prompt using the Azure OpenAI Client.  
- `pluginhelp(self)`: Provides help instructions for this plugin.  
- `plugincapabilities(self)`: Provides the plugin capabilities.  
  
#### Capabilities  
- `runprompt`: This capability allows running a prompt without retrieving any additional data. This plugin should be used if the user prompt doesn't require any additional or external data.  
  
### SentinelKQLPlugin  
  
This plugin generates and runs KQL queries adhering to the Sentinel schema.  
  
#### Methods  
- `__init__(self, name, description, plugintype, azureOpenAIClient, sentinelClient, loadSchema)`: Initializes the plugin with additional clients and schema loader.  
- `pluginhelp(self)`: Provides help instructions for this plugin.  
- `plugincapabilities(self)`: Provides the plugin capabilities.  
- `generateSentinelSchema(self)`: Generates the schema of Azure Sentinel tables.  
- `loadSentinelSchema(self)`: Loads the Sentinel schema from a JSON file, generating it if it doesn't exist.  
- `generateKQLandRun(self, prompt, session, channel)`: Generates a KQL query from a prompt and runs it.  
- `generateKQLandRunWithSchemaAndTable(self, prompt, table, session, channel)`: Generates a KQL query using the schema for a specific table and runs it.  
- `findTable(self, prompt, session, channel)`: Identifies the best table to use for a given prompt.  
- `runpromptonAzureAI(self, prompt, session)`: Runs a given prompt on the Azure OpenAI client.  
- `runtask(self, task, session, channel)`: Convenience method to run the task and generate a KQL query with schema.  
  
### FetchURLPlugin  
  
This plugin retrieves and processes data from a URL.  
  
#### Methods  
- `__init__(self, name, description, plugintype, azureOpenAIClient)`: Initializes the plugin with additional Azure OpenAI Client.  
- `plugincapabilities(self)`: Provides the plugin capabilities.  
- `pluginhelp(self)`: Provides help instructions for this plugin.  
- `clean_html(self, html_content)`: Cleans and extracts text from HTML content.  
- `download_and_clean_url(self, url)`: Downloads and cleans HTML content from a URL.  
- `runtask(self, prompt, session)`: Extracts the URL from the task and processes it.  
  
## Creating New Plugins  
  
To create a new plugin, follow these steps:  
  
1. **Create a New Plugin File**: Create a new Python file for your plugin in the `plugins` directory.  
2. **Import the Base Class**: Import the `TeisecAgentPlugin` class from `TeisecAgentPlugin.py`.  
3. **Define the Plugin Class**: Define your plugin class and inherit from `TeisecAgentPlugin`.  
4. **Implement Required Methods**:  
   - `__init__(self, name, description, plugintype, ...)`: Initialize your plugin with any additional parameters.  
   - `plugincapabilities(self)`: Provides the plugin capabilities.  
   - `runtask(self, task, session)`: Implement the functionality to process the task.  
   - `pluginhelp(self)`: Provide help instructions for your plugin.  
5. **Additional Methods**: Implement any additional methods required for your plugin's functionality.  
  
### Example  
  
```python  
from plugins.TeisecAgentPlugin import TeisecAgentPlugin  
  
class MyCustomPlugin(TeisecAgentPlugin):  
    def __init__(self, name, description, plugintype, custom_param):  
        super().__init__(name, description, plugintype)  
        self.custom_param = custom_param  
  
    def runtask(self, task, session):  
        # Custom processing logic  
        return f"Processed prompt with custom param: {self.custom_param}"  
    def plugincapabilities(self):  
        capabilities={'capability1':"This capability perform a set of actions"}
        return  capabilities
    def pluginhelp(self):  
        return "Use 'custom' in your prompt to trigger this plugin."  
```        
6. **Register the Plugin**: Ensure your plugin is registered in the main application to be utilized.  
   
By following these steps, you can easily extend the functionality of the Teisec Agent by adding new plugins tailored to specific tasks.