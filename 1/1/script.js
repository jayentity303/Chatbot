
const chatContainer = document.getElementById("chatContainer");

function appendMessage(text, role) {
  const wrap = document.createElement("div");
  wrap.classList.add("message", role);

  if (text.includes("```")) {
    const parts = text.split("```");
    // before first code
    if (parts[0].trim()) {
      const p = document.createElement("div");
      p.textContent = parts[0].trim();
      wrap.appendChild(p);
    }
    // code / after-code alternating
    for (let i = 1; i < parts.length; i += 2) {
      const codeBlock = document.createElement("div");
      codeBlock.className = "code-block";
      codeBlock.textContent = parts[i];
      wrap.appendChild(codeBlock);
      if (parts[i+1]?.trim()) {
        const p2 = document.createElement("div");
        p2.textContent = parts[i+1].trim();
        wrap.appendChild(p2);
      }
    }
  } else {
    wrap.textContent = text;
  }

  chatContainer.appendChild(wrap);
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

// Add keyboard shortcut for sending messages with Enter
document.getElementById("userInput").addEventListener("keydown", function(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});