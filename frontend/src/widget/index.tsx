import React from 'react';
import ReactDOM from 'react-dom/client';
import { Widget } from './Widget';
import { widgetStyles } from './styles';

function init() {
  // Find the script tag that loaded this widget
  const scripts = document.querySelectorAll('script[data-api-url]');
  const scriptTag = scripts[scripts.length - 1] as HTMLScriptElement | undefined;

  const apiUrl = scriptTag?.getAttribute('data-api-url') || '';
  const apiKey = scriptTag?.getAttribute('data-api-key') || undefined;

  if (!apiUrl) {
    console.error('[doc-qna-widget] Missing data-api-url attribute on script tag');
    return;
  }

  // Create host element
  const host = document.createElement('div');
  host.id = 'doc-qna-widget-host';
  document.body.appendChild(host);

  // Attach Shadow DOM for style isolation
  const shadowRoot = host.attachShadow({ mode: 'open' });

  // Inject styles
  const styleEl = document.createElement('style');
  styleEl.textContent = widgetStyles;
  shadowRoot.appendChild(styleEl);

  // Create mount point inside shadow root
  const mountPoint = document.createElement('div');
  shadowRoot.appendChild(mountPoint);

  // Render React into shadow DOM
  const root = ReactDOM.createRoot(mountPoint);
  root.render(
    React.createElement(Widget, { apiUrl, apiKey }),
  );
}

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
