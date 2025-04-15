document.addEventListener('DOMContentLoaded', () => {
    const chatbox = document.getElementById('chatbox');
    const messageInput = document.getElementById('messageInput');
    const sendButton = document.getElementById('sendButton');
    const modelSelect = document.getElementById('modelSelect');
    const maxTokensInput = document.getElementById('maxTokensInput');
    const statusDiv = document.getElementById('status');

    let conversationHistory = []; // Stores messages: { role: 'user' or 'assistant', content: '...' }

    // --- Helper: Add message to chatbox ---
    function addMessage(text, className) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', className);
        messageElement.textContent = text;
        chatbox.appendChild(messageElement);
        chatbox.scrollTo({ top: chatbox.scrollHeight, behavior: 'smooth' });
        return messageElement;
    }

    // --- Fetch models on load ---
    async function fetchModels() {
        statusDiv.textContent = 'Fetching models...';
        sendButton.disabled = true;
        try {
            const response = await fetch('/proxy/models');
            const data = await response.json();

            // Clear previous options
            modelSelect.innerHTML = '';

            // Check data format
            if (!data || !data.data || !Array.isArray(data.data)) {
                throw new Error('Invalid model data format received');
            }

            // Sort models by ID
            data.data.sort((a, b) => (a.id || '').localeCompare(b.id || ''));

            let defaultSelected = false;
            const popularModels = [
                'openai/gpt-4o-mini',
                'google/gemini-flash-1.5',
                'anthropic/claude-3-haiku',
                'openai/gpt-3.5-turbo'
            ];
            data.data.forEach(model => {
                if (!model.id) return;
                const option = document.createElement('option');
                option.value = model.id;
                option.textContent = (model.name && model.name !== model.id) ? `${model.name} (${model.id})` : model.id;
                modelSelect.appendChild(option);
                if (popularModels.includes(model.id) && !defaultSelected) {
                    option.selected = true;
                    defaultSelected = true;
                }
            });
            if (!defaultSelected && modelSelect.options.length > 0) {
                modelSelect.options[0].selected = true;
            }
            statusDiv.textContent = 'Models loaded. Ready.';
            sendButton.disabled = false;
        } catch (error) {
            console.error('Error fetching models:', error);
            statusDiv.textContent = `Error loading models: ${error.message}`;
            addMessage(`Error fetching models: ${error.message}. Please try reloading.`, 'system-info');
            sendButton.disabled = true;
        }
    }

    // --- Send message function ---
    async function sendMessage() {
        const messageText = messageInput.value.trim();
        const selectedModel = modelSelect.value;
        const maxTokens = maxTokensInput.value ? parseInt(maxTokensInput.value) : null;

        if (!messageText || sendButton.disabled) return;
        if (!selectedModel) {
            addMessage('Please select a model first.', 'system-info');
            return;
        }

        // Display user message and update conversation history
        addMessage(messageText, 'user-message');
        conversationHistory.push({ role: 'user', content: messageText });
        messageInput.value = '';
        messageInput.focus();
        sendButton.disabled = true;
        statusDiv.textContent = `Sending to ${selectedModel}...`;

        // Add placeholder for assistant response
        const assistantMessageElement = addMessage('...', 'assistant-message');

        try {
            const payload = {
                model: selectedModel,
                messages: conversationHistory,
                stream: true
            };
            if (maxTokens && maxTokens > 0) {
                payload.max_tokens = maxTokens;
            }

            const response = await fetch('/v1/completions', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream'
                },
                body: JSON.stringify(payload)
            });

            if (!response.ok || !response.body) {
                let errorDetails = `API Error (${response.status})`;
                try {
                    const errorData = await response.json();
                    errorDetails = `API Error: ${errorData.error || errorData.detail || JSON.stringify(errorData)}`;
                } catch (parseError) {
                    errorDetails = `API Error (${response.status}): ${response.statusText || 'Unknown error'}`;
                }
                throw new Error(errorDetails);
            }

            // --- SSE Streaming Decoder ---
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let fullResponse = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                // Split the buffer into lines, preserving any incomplete data in buffer
                const parts = buffer.split("\r\n");
                buffer = parts.pop(); // Save the incomplete line, if any

                for (const part of parts) {
                    // Process only lines beginning with "data:"
                    if (!part.startsWith("data:")) continue;
                    const jsonStr = part.slice(5).trim();  // Remove "data:" prefix

                    if (jsonStr === "[DONE]") {
                        statusDiv.textContent = "Response finished.";
                        break;
                    }

                    // Attempt to parse JSON chunk
                    try {
                        const json = JSON.parse(jsonStr);
                        const content = json.choices?.[0]?.delta?.content;
                        if (content) {
                            fullResponse += content;
                            assistantMessageElement.textContent = fullResponse;
                            chatbox.scrollTo({ top: chatbox.scrollHeight, behavior: "auto" });
                        }
                    } catch (e) {
                        // Silently ignore invalid chunks (e.g., empty or non-JSON markers)
                    }
                }
            }

            if (fullResponse) {
                conversationHistory.push({ role: 'assistant', content: fullResponse });
            }

        } catch (error) {
            console.error('Error sending message:', error);
            assistantMessageElement.textContent = `Error: ${error.message}`;
            statusDiv.textContent = `Error: ${error.message}`;
        } finally {
            sendButton.disabled = false;
            if (!statusDiv.textContent.includes('finished') && !statusDiv.textContent.includes('Error')) {
                statusDiv.textContent = 'Ready.';
            }
        }
    }

    // --- Event Listeners ---
    sendButton.addEventListener('click', sendMessage);
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // --- Initial load ---
    fetchModels();
});
