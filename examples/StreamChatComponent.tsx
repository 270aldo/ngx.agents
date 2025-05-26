import React, { useState, useRef, useEffect } from 'react';

interface Message {
  id: string;
  content: string;
  isUser: boolean;
  isStreaming?: boolean;
  timestamp: Date;
}

interface StreamChatProps {
  authToken: string;
  apiUrl?: string;
}

const StreamChatComponent: React.FC<StreamChatProps> = ({ 
  authToken, 
  apiUrl = 'http://localhost:8000' 
}) => {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [status, setStatus] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  // Auto-scroll al final cuando llegan nuevos mensajes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addMessage = (content: string, isUser: boolean, id?: string) => {
    const newMessage: Message = {
      id: id || Date.now().toString(),
      content,
      isUser,
      timestamp: new Date(),
      isStreaming: !isUser && isStreaming
    };
    
    setMessages(prev => [...prev, newMessage]);
    return newMessage.id;
  };

  const updateMessage = (id: string, content: string, isStreaming?: boolean) => {
    setMessages(prev => 
      prev.map(msg => 
        msg.id === id 
          ? { ...msg, content, isStreaming: isStreaming ?? msg.isStreaming }
          : msg
      )
    );
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isStreaming) return;

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setIsStreaming(true);
    setStatus('Conectando...');

    // Agregar mensaje del usuario
    addMessage(userMessage, true);

    // Crear ID para la respuesta del assistant
    const assistantMessageId = Date.now().toString();
    addMessage('', false, assistantMessageId);

    try {
      abortControllerRef.current = new AbortController();
      
      const response = await fetch(`${apiUrl}/stream/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${authToken}`,
          'Accept': 'text/event-stream',
        },
        body: JSON.stringify({
          message: userMessage,
          metadata: {
            client: 'react-sse',
            timestamp: new Date().toISOString()
          }
        }),
        signal: abortControllerRef.current.signal
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      setStatus('Recibiendo respuesta...');

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulatedContent = '';

      while (reader) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data:')) {
            const data = line.substring(5).trim();
            if (data) {
              try {
                const parsed = JSON.parse(data);
                
                if (parsed.type === 'content') {
                  accumulatedContent += parsed.content;
                  updateMessage(assistantMessageId, accumulatedContent, true);
                } else if (parsed.status === 'completed') {
                  updateMessage(assistantMessageId, accumulatedContent, false);
                  setStatus('Respuesta completada');
                } else if (parsed.status === 'error') {
                  throw new Error(parsed.error);
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      }

    } catch (error: any) {
      if (error.name === 'AbortError') {
        setStatus('Transmisión cancelada');
      } else {
        setStatus(`Error: ${error.message}`);
        updateMessage(assistantMessageId, `Error: ${error.message}`, false);
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  };

  const handleCancelStream = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  return (
    <div className="stream-chat-container">
      <div className="chat-header">
        <h2>NGX Agents - Chat con Streaming</h2>
        {status && <span className="status">{status}</span>}
      </div>

      <div className="messages-container">
        {messages.map(message => (
          <div 
            key={message.id} 
            className={`message ${message.isUser ? 'user' : 'assistant'} ${message.isStreaming ? 'streaming' : ''}`}
          >
            <div className="message-header">
              {message.isUser ? 'Tú' : 'NGX Agent'}
              <span className="timestamp">
                {message.timestamp.toLocaleTimeString()}
              </span>
            </div>
            <div className="message-content">
              {message.content || (message.isStreaming && '▌')}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-container">
        <input
          type="text"
          value={inputMessage}
          onChange={(e) => setInputMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="Escribe tu mensaje..."
          disabled={isStreaming}
          className="message-input"
        />
        {isStreaming ? (
          <button onClick={handleCancelStream} className="cancel-button">
            Cancelar
          </button>
        ) : (
          <button onClick={handleSendMessage} className="send-button">
            Enviar
          </button>
        )}
      </div>

      <style jsx>{`
        .stream-chat-container {
          max-width: 800px;
          margin: 0 auto;
          height: 600px;
          display: flex;
          flex-direction: column;
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          overflow: hidden;
          background-color: #fff;
        }

        .chat-header {
          padding: 1rem;
          background-color: #f5f5f5;
          border-bottom: 1px solid #e0e0e0;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .chat-header h2 {
          margin: 0;
          font-size: 1.25rem;
          color: #333;
        }

        .status {
          font-size: 0.875rem;
          color: #666;
          font-style: italic;
        }

        .messages-container {
          flex: 1;
          overflow-y: auto;
          padding: 1rem;
          background-color: #fafafa;
        }

        .message {
          margin-bottom: 1rem;
          animation: fadeIn 0.3s ease-in;
        }

        .message.user {
          text-align: right;
        }

        .message.assistant {
          text-align: left;
        }

        .message-header {
          font-size: 0.75rem;
          color: #666;
          margin-bottom: 0.25rem;
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .message.user .message-header {
          flex-direction: row-reverse;
        }

        .timestamp {
          font-size: 0.7rem;
          color: #999;
          margin: 0 0.5rem;
        }

        .message-content {
          display: inline-block;
          padding: 0.75rem 1rem;
          border-radius: 1rem;
          max-width: 70%;
          word-wrap: break-word;
        }

        .message.user .message-content {
          background-color: #007bff;
          color: white;
          text-align: left;
        }

        .message.assistant .message-content {
          background-color: #e9ecef;
          color: #333;
        }

        .message.streaming .message-content::after {
          content: '▌';
          animation: blink 1s infinite;
        }

        .input-container {
          display: flex;
          padding: 1rem;
          border-top: 1px solid #e0e0e0;
          background-color: #fff;
        }

        .message-input {
          flex: 1;
          padding: 0.75rem;
          border: 1px solid #ddd;
          border-radius: 4px;
          font-size: 1rem;
          outline: none;
        }

        .message-input:focus {
          border-color: #007bff;
        }

        .send-button, .cancel-button {
          margin-left: 0.5rem;
          padding: 0.75rem 1.5rem;
          border: none;
          border-radius: 4px;
          font-size: 1rem;
          cursor: pointer;
          transition: background-color 0.2s;
        }

        .send-button {
          background-color: #007bff;
          color: white;
        }

        .send-button:hover {
          background-color: #0056b3;
        }

        .cancel-button {
          background-color: #dc3545;
          color: white;
        }

        .cancel-button:hover {
          background-color: #c82333;
        }

        .send-button:disabled {
          background-color: #ccc;
          cursor: not-allowed;
        }

        @keyframes fadeIn {
          from {
            opacity: 0;
            transform: translateY(10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes blink {
          0%, 50% { opacity: 1; }
          51%, 100% { opacity: 0; }
        }
      `}</style>
    </div>
  );
};

export default StreamChatComponent;