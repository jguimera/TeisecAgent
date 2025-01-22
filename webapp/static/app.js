const socket = io.connect(location.protocol+'//' + document.domain + ':' + location.port + '/teisec');  
const messagesContainer = document.getElementById('messages');  
const inputField = document.getElementById('input');  
const sendButton = document.getElementById('send');  
const clearButton = document.getElementById('clear');  
const toggleDebugButton = document.getElementById('toggle-debug');  
const loadingMessage = document.getElementById('loading-message');  
const debugPanel = document.getElementById('debug-panel');  
const debugMessagesContainer = document.getElementById('debug-messages');

const sessionId = window.location.pathname.split('/').pop();

document.getElementById('toggle-system').addEventListener('change', function() {
    const systemMessages = document.querySelectorAll('.system-message');
    if (this.checked) {
        systemMessages.forEach(message => {
            message.classList.remove('hidden');
        });
    } else {
        systemMessages.forEach(message => {
            message.classList.add('hidden');
        });
    }
 });
function getChatBoxStyle(variant) {
    switch (variant) {
        case 'bot':
            return 'text-sm bg-indigo-300 text-black';
        case 'system':
            var classes='text-xs bg-neutral-300 text-black system-message'
            if (!document.getElementById('toggle-system').checked) {
                classes += ' hidden';
            }
            return classes;
        default:
            return 'text-sm bg-lime-600';
    }
}

function addMessage(response, variant) {  
    const containerClassName = variant !== 'bot' ? 'flex justify-end' : 'flex justify-start';
    const messageElement = document.createElement('div'); 
    const chatBoxStyle = getChatBoxStyle(variant)
    const messageElementTemplate = `
        <div class="p-2 mb-1 ${chatBoxStyle} rounded-xl shadow-lg flex items-center gap-x-4 overflow-x-auto max-w-screen-lg lg:max-w-screen-xl  text-white">                
            ${response}
        </div>
    ` 
    messageElement.className = containerClassName;
    messageElement.innerHTML = messageElementTemplate;  
    messagesContainer.appendChild(messageElement);  
    messagesContainer.scrollTop = messagesContainer.scrollHeight;  
}  

function handleUserInput() {  
    const userInput = inputField.value.trim();  
    if (userInput) {  
        addMessage(userInput, 'user');  
        socket.emit('prompt', { 'sessionId':sessionId, "user_prompt":userInput });  
        inputField.value = '';  
        showLoadingMessage();  
    }  
}

function showLoadingMessage() {  
    loadingMessage.setAttribute('data-open', 'true');
}  

function hideLoadingMessage() {  
    loadingMessage.setAttribute('data-open', 'false');
}  
document.getElementById('open-session').addEventListener('click', function() {
    window.open('/session/' + sessionId, '_blank');
});
sendButton.addEventListener('click', handleUserInput);  

inputField.addEventListener('keypress', function(event) {  
    if (event.key === 'Enter') {  
        handleUserInput();  
    }  
});  

clearButton.addEventListener('click', function() {  
    messagesContainer.innerHTML = '';
    hideLoadingMessage();  
    socket.emit('clear_session', {"sessionId": sessionId });  

});  

toggleDebugButton.addEventListener('click', function() {  
    debugPanel.classList.toggle('visible');
    if (debugPanel.classList.contains('visible')) {
        toggleDebugButton.textContent = 'Hide Debug';
    } else {
        toggleDebugButton.textContent = 'Show Debug';
    }
});  

document.addEventListener('click', function(event) {  
    if (!debugPanel.contains(event.target) && !toggleDebugButton.contains(event.target)) {  
        debugPanel.classList.remove('visible');
        toggleDebugButton.textContent = 'Show Debug';
    }  
});  

function loadSessionMessages(sessionId) {
    fetch(`/session/raw/${sessionId}`)
        .then(response => response.json())
        .then(data => {
            const tasks = data.tasks;
            messagesContainer.innerHTML = ''; // Clear existing messages
            tasks.forEach(task => {
                addMessage(task.task, 'user');
                addMessage(task.processed_response.result, 'bot');
            });
        })
        .catch(error => console.error('Error loading session messages:', error));
}

// Load session messages on page load
document.addEventListener('DOMContentLoaded', function() {
    loadSessionMessages(sessionId);
});

socket.on('completedmessage', function(message_object) {  
    hideLoadingMessage();    
});
socket.on('resultmessage', function(message_object) {  
    addMessage(message_object.message, 'bot');  
});  
socket.on('systemmessage', function(message_object) {  
    addMessage(message_object.message, 'system');
});  
socket.on('debugmessage', function(message_object) {  
    const debugMessageElement = document.createElement('div');  
    debugMessageElement.textContent = message_object.message;  
    debugMessagesContainer.appendChild(debugMessageElement);  
    debugMessagesContainer.scrollTop = debugMessagesContainer.scrollHeight;  
});  
socket.on('actionmessage', function(message_object) {  
    action=message_object.action;
    if (action=='NewSession') {
        newSessionId = message_object.sessionId;
        const newUrl = `/session/${newSessionId}`;
        window.location.href = newUrl;
    }
});
