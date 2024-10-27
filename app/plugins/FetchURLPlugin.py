from app.plugins.TeisecAgentPlugin import TeisecAgentPlugin  
import requests  
from requests.exceptions import MissingSchema,InvalidSchema,ChunkedEncodingError
from bs4 import BeautifulSoup  
 
class FetchURLPlugin(TeisecAgentPlugin):  
    """  
    Plugin to fetch and process data from a URL.  
    """  
  
    def __init__(self, name, description, plugintype, azureOpenAIClient):  
        """  
        Initialize the FetchURLPlugin.  
  
        :param name: Name of the plugin  
        :param description: Description of the plugin  
        :param plugintype: Type of the plugin  
        :param azureOpenAIClient: Azure OpenAI Client instance  
        """  
        super().__init__(name, description, plugintype)  
        self.azureOpenAIClient = azureOpenAIClient  
  
    def pluginhelp(self):  
        """  
        Provide help instructions for this plugin.  
  
        :return: Help instructions string  
        """  
        return "Use 'fetch', 'url', or 'download' in your prompt to retrieve data from a URL and process it."  
  
    def plugincapabilities(self):  
        """  
        Provide the plugin capabilities.  
  
        :return: plugin capabilities object  
        """  
        capabilities={'fetchurl':"This capability retrieves data from external urls or site to be processed inside the session.It requires a valid URL in the prompt "}
        return  capabilities
    def clean_html(self, html_content):  
        """  
        Clean and extract text from HTML content.  
  
        :param html_content: Raw HTML content  
        :return: Cleaned text  
        """  
        soup = BeautifulSoup(html_content, 'html.parser')  
  
        # Remove all script and style elements  
        for script_or_style in soup(['script', 'style']):  
            script_or_style.decompose()  
  
        # Extract text  
        text = soup.get_text()  
  
        # Break into lines and remove leading/trailing space on each  
        lines = (line.strip() for line in text.splitlines())  
  
        # Break multi-headlines into a line each  
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))  
  
        # Drop blank lines  
        cleaned_text = '\n'.join(chunk for chunk in chunks if chunk)  
  
        return cleaned_text  
  
    def download_and_clean_url(self, url):  
        """  
        Download content from a URL and clean it.  
  
        :param url: URL to fetch content from  
        :return: Cleaned text from the URL  
        """  
        try:    
            response = requests.get(url)  

            if response.status_code == 200:  
                cleaned_text = self.clean_html(response.content)  
                return cleaned_text  
            else:  
                return f"Failed to retrieve content. Status code: {response.status_code}" 
        except MissingSchema as e:  
            return f"Failed to retrieve content. URL couldn't be extracted from the prompt."  
        except InvalidSchema as e: 
            return f"Failed to retrieve content. URL couldn't be extracted from the prompt."  
        except ChunkedEncodingError as e:  
            return f"Failed to retrieve content. URL couldn't be extracted from the prompt."  
    def fetchAndClean(self, prompt, session,channel):  
        """  
        Extract the URL from the prompt and process it.  
  
        :param prompt: Input prompt  
        :param session: Session context  
        :return: Processed content from the URL  
        """  
        # Extend the prompt to instruct the extraction of the URL  
        extended_prompt = (  
            'You are part of a system that downloads and processes HTML content. '  
            'I need you to extract the URL from the following prompt (Only return the URL to be sent as a parameter to a Python function): ' + prompt  
        )  
  
        # Use the Azure OpenAI Client to extract the URL from the prompt  
        result_object = self.azureOpenAIClient.runPrompt(extended_prompt, session)  
        if result_object['status']=='success':
            # Download and clean the content from the extracted URL
            prompt_result=result_object['result']
            url=prompt_result.replace("```plaintext", "").replace("```", "").replace("\n", "").strip()   
            result_object['result']=self.download_and_clean_url(url)
            return result_object
        else:
            return result_object
    def runtask(self, task, session,channel):  
        """  
        Convenience method to run the tasks inside the plugin.  
        :param task: Input task  
        :param session: Session context  
        :return: Result of the task execution 
        """
        return self.fetchAndClean(task["task"],session,channel)