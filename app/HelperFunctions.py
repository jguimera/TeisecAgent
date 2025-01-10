from colorama import Fore
import json
def print_info(text):
    print(f"{Fore.GREEN}[Info] {Fore.WHITE}"+text)
def print_debug(text):
    print(f"{Fore.MAGENTA}[Debug] {Fore.WHITE}"+text)
def print_plugin_debug(plugin_name,text):
    print(f"{Fore.MAGENTA}[Plugin Debug]({plugin_name}) {Fore.WHITE}"+text)
def print_help(text):
    print(f"{Fore.BLUE}[Help]{Fore.WHITE} "+text)
def print_response(text):
    print(f"{Fore.CYAN}[Response]{Fore.WHITE} "+text)
def print_error(text):
    print(f"{Fore.RED}[Error] {Fore.WHITE}"+text)
def saveToFile(content):
        user_input = input("Type a filename to save the JSON results in a file. Type N to keep prompting:")
        if "N" == user_input or "n" == user_input:
            response='Results Discarded. You can Keep prompting'
        else:
            with open(user_input, 'w', encoding='utf-8') as f:
                json.dump(content, f, ensure_ascii=False, indent=4)
                f.close()
            response='File Saved:'+user_input
        return response
def print_intro_message():  
    """  
    Print the introductory message for the assistant.  
    """  
    message = '''
╔╦╗╔═╗╦╔═╗╔═╗╔═╗  ╔═╗╔═╗╔═╗╔╗╔╔╦╗
 ║ ║╣ ║╚═╗║╣ ║    ╠═╣║ ╦║╣ ║║║ ║ 
 ╩ ╚═╝╩╚═╝╚═╝╚═╝  ╩ ╩╚═╝╚═╝╝╚╝ ╩ 
            '''
    print(f"{Fore.GREEN}{message}{Fore.WHITE}")  
    print_info("Welcome to Teisec Agent")  