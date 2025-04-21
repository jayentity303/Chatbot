// DOM elements
const chatContainer = document.getElementById('chat-messages');
const chatForm = document.getElementById('chat-form');
const userInput = document.getElementById('userInput');
const textModelSelect = document.getElementById('text_model');
const streamToggle = document.getElementById('streamToggle');
const currentModelDisplay = document.getElementById('current-model');

// — Model selector display —
textModelSelect.addEventListener('change', () => {
    currentModelDisplay.textContent = textModelSelect.value;
  });
  if (textModelSelect.options.length > 0) {
    currentModelDisplay.textContent = textModelSelect.value;
  }
  
  // — Textarea auto‑resize/reset —
  userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 150) + 'px';
  });
  function resetTextareaHeight() {
    userInput.style.height = 'auto';
  }

  function createCodeBlockHTML(code, language) {
    const langClass   = language ? ` class="language-${language}"` : '';
    const langDisplay = language || 'plaintext';
    return `
      <div class="code-block-wrapper">
        <div class="code-block-header">
          <span class="code-block-language">${langDisplay}</span>
          <div class="code-block-actions">
            <button class="copy-btn" onclick="copyCode(this)">Copy</button>
          </div>
        </div>
        <pre><code${langClass}>${code}</code></pre>
      </div>
    `;
  }
  
  function processMessageContent(text) {
    text = text.replace(/```([a-z]*)\n([\s\S]*?)```/g,
      (_, lang, code) => createCodeBlockHTML(code, lang)
    );
    text = text.replace(/```\n?([\s\S]*?)```/g,
      (_, code) => createCodeBlockHTML(code, '')
    );
    return text.replace(/\n/g, '<br>');
  }
  
  function highlightCode(el) {
    el.querySelectorAll('pre code').forEach(block => {
      Prism.highlightElement(block);
    });
  }
  
  window.copyCode = button => {
    const code = button
      .closest('.code-block-wrapper')
      .querySelector('code')
      .textContent;
    navigator.clipboard.writeText(code).then(() => {
      const old = button.textContent;
      button.textContent = 'Copied!';
      setTimeout(() => button.textContent = old, 2000);
    });
  };
  

// Update displayed model name when selection changes
textModelSelect.addEventListener('change', () => {
  currentModelDisplay.textContent = textModelSelect.value;
});

// Initialize with first model
if (textModelSelect.options.length > 0) {
  currentModelDisplay.textContent = textModelSelect.value;
}

// Auto-resize textarea as user types
userInput.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 150) + 'px';
});

// Reset textarea height when form is submitted
function resetTextareaHeight() {
  userInput.style.height = 'auto';
}

// Process code blocks with Prism.js
function highlightCode(element) {
  const codeBlocks = element.querySelectorAll('pre code');
  codeBlocks.forEach((block) => {
    // Try to determine language
    let language = '';
    const classes = block.className.split(' ');
    for (const cls of classes) {
      if (cls.startsWith('language-')) {
        language = cls.substring(9);
        break;
      }
    }
    
    if (!language) {
      // If no language specified, try to guess from content
      if (block.textContent.includes('def ') || block.textContent.includes('import ')) {
        language = 'python';
      } else if (block.textContent.includes('function') || block.textContent.includes('const ')) {
        language = 'javascript';
      } else if (block.textContent.includes('<div') || block.textContent.includes('</div>')) {
        language = 'html';
      } else if (block.textContent.includes('{') && block.textContent.includes(':')) {
        language = 'json';
      }
      
      if (language) {
        block.className = `language-${language}`;
      }
    }
  });
  
  // Apply Prism highlighting
  Prism.highlightAllUnder(element);
}

// Create message container with proper structure
function createMessageContainer(role, content) {
  const container = document.createElement('div');
  container.className = 'message-container';
  
  const header = document.createElement('div');
  header.className = 'message-header';
  
  const avatar = document.createElement('div');
  avatar.className = `avatar ${role}`;
  avatar.textContent = role === 'user' ? 'U' : 'C';
  
  const roleName = document.createElement('div');
  roleName.className = 'message-role';
  roleName.textContent = role === 'user' ? 'You' : 'Claude';
  
  header.appendChild(avatar);
  header.appendChild(roleName);
  
  const messageContent = document.createElement('div');
  messageContent.className = 'message-content';
  
  // Process content
  if (typeof content === 'string') {
    messageContent.innerHTML = processMessageContent(content);
  } else {
    messageContent.appendChild(content);
  }
  
  container.appendChild(header);
  container.appendChild(messageContent);
  
  return container;
}

// Process message content to handle code blocks and markdown
function processMessageContent(text) {
  // First replace ```code``` blocks with proper HTML
  let processed = text;
  
  // Process code blocks with language specification: ```python
  const codeBlockRegex = /```([a-z]*)\n([\s\S]*?)```/g;
  processed = processed.replace(codeBlockRegex, (match, language, code) => {
    return createCodeBlockHTML(code, language);
  });
  
  // Process code blocks without language specification: ```
  const simpleCodeBlockRegex = /```\n?([\s\S]*?)```/g;
  processed = processed.replace(simpleCodeBlockRegex, (match, code) => {
    return createCodeBlockHTML(code, '');
  });
  
  // Replace newlines with <br> for line breaks
  processed = processed.replace(/\n/g, '<br>');
  
  return processed;
}

// Create HTML for code blocks with syntax highlighting
function createCodeBlockHTML(code, language) {
  const langClass = language ? ` class="language-${language}"` : '';
  const langDisplay = language || 'plaintext';
  
  return `
    <div class="code-block-wrapper">
      <div class="code-block-header">
        <span class="code-block-language">${langDisplay}</span>
        <div class="code-block-actions">
          <button class="code-action-btn copy-btn" onclick="copyCode(this)">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M8 4v12a2 2 0 002 2h8a2 2 0 002-2V8.342a2 2 0 00-.602-1.43l-4.44-4.342A2 2 0 0013.56 2H10a2 2 0 00-2 2z" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              <path d="M16 18v2a2 2 0 01-2 2H6a2 2 0 01-2-2V9a2 2 0 012-2h2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
            </svg>
            Copy
          </button>
        </div>
      </div>
      <pre class="code-block code-block-with-header"><code${langClass}>${code}</code></pre>
    </div>
  `;
}

// Function to copy code to clipboard
window.copyCode = function(button) {
  const codeBlock = button.closest('.code-block-wrapper').querySelector('code');
  const textToCopy = codeBlock.textContent;
  
  navigator.clipboard.writeText(textToCopy).then(() => {
    // Success feedback
    const originalText = button.innerHTML;
    button.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M20 6L9 17l-5-5" stroke="#52c41a" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
      Copied!
    `;
    button.style.color = 'var(--success-color)';
    
    // Reset after a short delay
    setTimeout(() => {
      button.innerHTML = originalText;
      button.style.color = '';
    }, 2000);
  });
};

// Function to append user message
function appendUserMessage(text) {
  const messageContainer = createMessageContainer('user', text);
  chatContainer.appendChild(messageContainer);
  scrollToBottom();
}

// Function to append assistant message
function appendAssistantMessage(text) {
  const messageContainer = createMessageContainer('assistant', text);
  chatContainer.appendChild(messageContainer);
  highlightCode(messageContainer);
  scrollToBottom();
}

// Function to create and append streaming message container
function createStreamingMessage() {
  const container = document.createElement('div');
  container.className = 'message-container';
  
  const header = document.createElement('div');
  header.className = 'message-header';
  
  const avatar = document.createElement('div');
  avatar.className = 'avatar assistant';
  avatar.textContent = 'C';
  
  const roleName = document.createElement('div');
  roleName.className = 'message-role';
  roleName.textContent = 'Claude';
  
  header.appendChild(avatar);
  header.appendChild(roleName);
  
  const messageContent = document.createElement('div');
  messageContent.className = 'message-content streaming-content';
  
  container.appendChild(header);
  container.appendChild(messageContent);
  chatContainer.appendChild(container);
  
  return messageContent;
}

// Function to append images
function appendImages(images) {
    const wrapper = document.createElement("div");
    wrapper.classList.add("message", "assistant");
    const grid = document.createElement("div");
    grid.classList.add("image-grid");
    images.forEach(uri => {
      const img = document.createElement("img");
      img.src = uri;
      grid.appendChild(img);
    });
    wrapper.appendChild(grid);
    chatContainer.appendChild(wrapper);
    chatContainer.scrollTop = chatContainer.scrollHeight;
  }

function appendImages(images) {
  const wrapper = document.createElement("div");
  wrapper.classList.add("message", "assistant");
  const grid = document.createElement("div");
  grid.classList.add("image-grid");
  images.forEach(uri => {
    const img = document.createElement("img");
    img.src = uri;
    grid.appendChild(img);
  });
  wrapper.appendChild(grid);
  chatContainer.appendChild(wrapper);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Function to scroll chat to bottom
function scrollToBottom() {
  const chatContainerEl = document.getElementById('chat-container');
  chatContainerEl.scrollTop = chatContainerEl.scrollHeight;
}

// Function to send message
function sendMessage() {
    const input = document.getElementById("userInput").value.trim();
    if (!input) return;

    appendMessage(input, "user");
    document.getElementById("userInput").value = "";
    
    const isStreaming = document.getElementById("streamToggle").checked;
    const isImageRequest = input.toLowerCase().startsWith("-img");
    
    // For image requests or non-streaming, use regular fetch with JSON
    if (isImageRequest || !isStreaming) {
      fetch("/process_request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          input,
          text_model: document.getElementById("text_model").value,
          image_model: document.getElementById("image_model").value,
          stream: isStreaming
        })
      })
      .then(res => res.json())
      .then(data => {
        appendMessage(data.output, "assistant");
        if (data.images && data.images.length) {
          appendImages(data.images);
        }
      })
      .catch(err => {
        appendMessage("❌ " + err.message, "assistant");
      });
    } 
    // For streaming text responses, use EventSource
    else {
      // Create an empty message to stream into
      const streamMsg = document.createElement("div");
      streamMsg.classList.add("message", "assistant");
      chatContainer.appendChild(streamMsg);
      
      // Setup event source for streaming
      const source = new EventSource(`/stream?input=${encodeURIComponent(input)}&model=${encodeURIComponent(document.getElementById("text_model").value)}`);
      
      source.onmessage = function(event) {
        streamMsg.textContent += event.data;
        chatContainer.scrollTop = chatContainer.scrollHeight;
      };
      
      source.onerror = function() {
        source.close();
      };
    }
  }

// Add keyboard shortcut for sending messages with Enter (but keep Shift+Enter for new lines)
userInput.addEventListener('keydown', function(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

// Event listeners
chatForm.addEventListener('submit', sendMessage);

// Load chat history
function loadChatHistory() {
  fetch('/get_chat_history')
    .then(res => res.json())
    .then(chats => {
      if (chats.length > 0) {
        // Clear any default welcome message
        chatContainer.innerHTML = '';
        
        // Display most recent chats (reversed to show oldest first)
        chats.reverse().slice(0, 10).forEach(chat => {
          appendUserMessage(chat.input_text);
          if (chat.is_image_request && chat.images && chat.images.length > 0) {
            appendAssistantMessage(chat.output_text);
            appendImages(chat.images);
          } else {
            appendAssistantMessage(chat.output_text);
          }
        });
      }
    })
    .catch(err => console.error('Failed to load chat history:', err));
}

// Initialize the interface
window.addEventListener('load', function() {
  // Focus on input field
  userInput.focus();
  
  // You can uncomment this to load previous chat history
  // loadChatHistory();
});