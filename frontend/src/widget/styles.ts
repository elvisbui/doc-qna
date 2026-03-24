export const widgetStyles = `
  :host {
    all: initial;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  }

  * {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }

  .widget-button {
    position: fixed;
    bottom: 16px;
    right: 16px;
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background-color: #2563eb;
    color: white;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    transition: background-color 0.2s, transform 0.2s;
    z-index: 2147483647;
  }

  .widget-button:hover {
    background-color: #1d4ed8;
    transform: scale(1.05);
  }

  .widget-button svg {
    width: 24px;
    height: 24px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.5;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .chat-panel {
    position: fixed;
    bottom: 80px;
    right: 16px;
    width: 400px;
    height: 600px;
    max-height: calc(100vh - 100px);
    background: white;
    border-radius: 12px;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    z-index: 2147483647;
    animation: slideUp 0.2s ease-out;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(8px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .chat-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px;
    background: #2563eb;
    color: white;
    flex-shrink: 0;
  }

  .chat-header-title {
    font-size: 16px;
    font-weight: 600;
  }

  .close-button {
    background: none;
    border: none;
    color: white;
    cursor: pointer;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .close-button:hover {
    background-color: rgba(255, 255, 255, 0.2);
  }

  .close-button svg {
    width: 20px;
    height: 20px;
    fill: none;
    stroke: currentColor;
    stroke-width: 2;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .message-list {
    flex: 1;
    overflow-y: auto;
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .message-list-empty {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    color: #9ca3af;
    font-size: 14px;
    text-align: center;
    padding: 16px;
  }

  .message {
    max-width: 85%;
    padding: 10px 14px;
    border-radius: 12px;
    font-size: 14px;
    line-height: 1.5;
    word-wrap: break-word;
    white-space: pre-wrap;
  }

  .message-user {
    align-self: flex-end;
    background-color: #2563eb;
    color: white;
    border-bottom-right-radius: 4px;
  }

  .message-assistant {
    align-self: flex-start;
    background-color: #f3f4f6;
    color: #1f2937;
    border-bottom-left-radius: 4px;
  }

  .message-error {
    align-self: center;
    background-color: #fef2f2;
    color: #dc2626;
    font-size: 13px;
  }

  .streaming-cursor {
    display: inline-block;
    width: 6px;
    height: 16px;
    background-color: #9ca3af;
    margin-left: 2px;
    vertical-align: text-bottom;
    border-radius: 1px;
    animation: blink 1s step-end infinite;
  }

  @keyframes blink {
    50% { opacity: 0; }
  }

  .loading-dots {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 0;
  }

  .loading-dots span {
    width: 8px;
    height: 8px;
    background-color: #9ca3af;
    border-radius: 50%;
    animation: bounce 1.4s ease-in-out infinite;
  }

  .loading-dots span:nth-child(2) {
    animation-delay: 0.15s;
  }

  .loading-dots span:nth-child(3) {
    animation-delay: 0.3s;
  }

  @keyframes bounce {
    0%, 80%, 100% { transform: translateY(0); }
    40% { transform: translateY(-6px); }
  }

  .chat-input-area {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid #e5e7eb;
    background: white;
    flex-shrink: 0;
  }

  .chat-input {
    flex: 1;
    resize: none;
    border: 1px solid #d1d5db;
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 14px;
    font-family: inherit;
    line-height: 1.4;
    outline: none;
    transition: border-color 0.2s;
    max-height: 120px;
    min-height: 40px;
  }

  .chat-input:focus {
    border-color: #2563eb;
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
  }

  .chat-input::placeholder {
    color: #9ca3af;
  }

  .send-button {
    flex-shrink: 0;
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 16px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: background-color 0.2s;
    font-family: inherit;
  }

  .send-button:hover:not(:disabled) {
    background-color: #1d4ed8;
  }

  .send-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;
