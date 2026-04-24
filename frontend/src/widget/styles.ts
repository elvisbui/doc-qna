export const widgetStyles = `
  :host {
    all: initial;
    font-family:
      "Söhne", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont,
      "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
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
    width: 48px;
    height: 48px;
    border-radius: 50%;
    background-color: #0d0d0d;
    color: #ffffff;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.12);
    transition: opacity 0.15s;
    z-index: 2147483647;
  }

  .widget-button:hover {
    opacity: 0.9;
  }

  .widget-button svg {
    width: 22px;
    height: 22px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.5;
    stroke-linecap: round;
    stroke-linejoin: round;
  }

  .chat-panel {
    position: fixed;
    bottom: 76px;
    right: 16px;
    width: 384px;
    height: 560px;
    max-height: calc(100vh - 100px);
    background: #ffffff;
    border: 1px solid #ececec;
    border-radius: 16px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    z-index: 2147483647;
    animation: slideUp 0.18s ease-out;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(6px);
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
    padding: 12px 16px;
    border-bottom: 1px solid #ececec;
    background: #ffffff;
    color: #0d0d0d;
    flex-shrink: 0;
  }

  .chat-header-title {
    font-size: 14px;
    font-weight: 600;
  }

  .close-button {
    background: none;
    border: none;
    color: #5d5d5d;
    cursor: pointer;
    padding: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 6px;
    transition: background-color 0.15s, color 0.15s;
  }

  .close-button:hover {
    background-color: #f2f2f2;
    color: #0d0d0d;
  }

  .close-button svg {
    width: 18px;
    height: 18px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.75;
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
    color: #8e8e8e;
    font-size: 14px;
    text-align: center;
    padding: 16px;
  }

  .message {
    max-width: 85%;
    font-size: 14px;
    line-height: 1.55;
    word-wrap: break-word;
    white-space: pre-wrap;
    letter-spacing: -0.003em;
  }

  .message-user {
    align-self: flex-end;
    background-color: #f2f2f2;
    color: #0d0d0d;
    padding: 9px 14px;
    border-radius: 18px;
  }

  .message-assistant {
    align-self: flex-start;
    background: transparent;
    color: #0d0d0d;
    padding: 0;
  }

  .message-error {
    align-self: center;
    color: #5d5d5d;
    font-size: 13px;
  }

  .streaming-cursor {
    display: inline-block;
    width: 6px;
    height: 14px;
    background-color: #0d0d0d;
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
    gap: 5px;
    padding: 4px 0;
  }

  .loading-dots span {
    width: 6px;
    height: 6px;
    background-color: #8e8e8e;
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
    40% { transform: translateY(-4px); }
  }

  .chat-input-area {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    padding: 12px 16px;
    border-top: 1px solid #ececec;
    background: #ffffff;
    flex-shrink: 0;
  }

  .chat-input {
    flex: 1;
    resize: none;
    border: 1px solid #ececec;
    border-radius: 12px;
    padding: 9px 12px;
    font-size: 14px;
    font-family: inherit;
    line-height: 1.45;
    outline: none;
    transition: border-color 0.15s;
    max-height: 120px;
    min-height: 38px;
    color: #0d0d0d;
    background: #ffffff;
  }

  .chat-input:focus {
    border-color: #8e8e8e;
  }

  .chat-input::placeholder {
    color: #8e8e8e;
  }

  .send-button {
    flex-shrink: 0;
    background-color: #0d0d0d;
    color: #ffffff;
    border: none;
    border-radius: 999px;
    padding: 8px 14px;
    font-size: 13px;
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.15s;
    font-family: inherit;
  }

  .send-button:hover:not(:disabled) {
    opacity: 0.9;
  }

  .send-button:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }
`;
