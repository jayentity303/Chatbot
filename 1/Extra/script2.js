const chatContainer = document.getElementById("chatContainer");

// — Model selector display — (from script1.js)
const textModelSelect = document.getElementById('text_model');
const currentModelDisplay = document.getElementById('current-model');

textModelSelect.addEventListener('change', () => {
  currentModelDisplay.textContent = textModelSelect.value;
});

if (textModelSelect.options.length > 0) {
  currentModelDisplay.textContent = textModelSelect.value;
}

// — Textarea auto‑resize/reset — (improved from script1.js)
const userInput = document.getElementById("userInput");

userInput.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = Math.min(this.scrollHeight, 150) + 'px';
});

function resetTextareaHeight() {
  userInput.style.height = 'auto';
}

// Process code blocks with proper styling (from script1.js)
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

// Process message content with improved code block handling (from script1.js)
function processMessageContent(text) {
  // Process code blocks with language specification: ```python
  let processed = text;
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

// Syntax highlighting function (from script1.js)
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

// Function to copy code to clipboard (from script1.js)
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

// Enhanced message appending function (combining both files)
function appendMessage(text, role) {
  const container = document.createElement('div');
  container.className = `message-container ${role}`;
  
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
  
  if (text.includes("```")) {
    messageContent.innerHTML = processMessageContent(text);
  } else {
    messageContent.innerHTML = text.replace(/\n/g, '<br>');
  }
  
  container.appendChild(header);
  container.appendChild(messageContent);
  
  chatContainer.appendChild(container);
  
  if (role === 'assistant') {
    highlightCode(messageContent);
  }
  
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

// Enhanced image appending function
function appendImages(images) {
  const wrapper = document.createElement("div");
  wrapper.classList.add("message-container", "assistant");
  
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
  
  wrapper.appendChild(header);
  
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

function sendMessage() {
  const input = document.getElementById("userInput").value.trim();
  if (!input) return;

  appendMessage(input, "user");
  document.getElementById("userInput").value = "";
  resetTextareaHeight();
  
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
    // Create an empty message container with header for streaming
    const container = document.createElement('div');
    container.className = 'message-container assistant';
    
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
    
    const streamMsg = document.createElement('div');
    streamMsg.className = 'message-content streaming-content';
    
    container.appendChild(header);
    container.appendChild(streamMsg);
    chatContainer.appendChild(container);
    
    // Setup event source for streaming
    const source = new EventSource(`/stream?input=${encodeURIComponent(input)}&model=${encodeURIComponent(document.getElementById("text_model").value)}`);
    
    let fullContent = '';
    
    source.onmessage = function(event) {
      fullContent += event.data;
      
      // Check if we need to process code blocks
      if (fullContent.includes('```')) {
        streamMsg.innerHTML = processMessageContent(fullContent);
        highlightCode(streamMsg);
      } else {
        streamMsg.innerHTML = fullContent.replace(/\n/g, '<br>');
      }
      
      chatContainer.scrollTop = chatContainer.scrollHeight;
    };
    
    source.onerror = function() {
      source.close();
    };
  }
}

// Add keyboard shortcut for sending messages with Enter
userInput.addEventListener("keydown", function(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});

// Optional: Load chat history on page load
function loadChatHistory() {
  fetch('/get_chat_history')
    .then(res => res.json())
    .then(chats => {
      if (chats.length > 0) {
        // Display most recent chats (reversed to show oldest first)
        chats.reverse().slice(0, 10).forEach(chat => {
          appendMessage(chat.input_text, "user");
          if (chat.is_image_request && chat.images && chat.images.length > 0) {
            appendMessage(chat.output_text, "assistant");
            appendImages(chat.images);
          } else {
            appendMessage(chat.output_text, "assistant");
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
  
  // Uncomment to load previous chat history
  // loadChatHistory();
});