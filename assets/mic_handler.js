(function() {
  const parentDoc = window.parent.document;
  const scriptTag = document.currentScript;
  const speechLangCode = scriptTag ? scriptTag.getAttribute("data-lang") : "en-IN";
  
  function inject() {
      // Prevent multiple injections
      if (parentDoc.getElementById('micBtnWrap')) return true;

      // Find the chat input container
      const chatInputContainer = parentDoc.querySelector('[data-testid="stChatInput"]');
      if (!chatInputContainer) return false;

      // Add custom styles to parent document
      if (!parentDoc.getElementById('micStyles')) {
        const style = parentDoc.createElement('style');
        style.id = 'micStyles';
        style.textContent = `
          #micBtnWrap {
            position: absolute;
            right: 3.5rem;
            bottom: 50%;
            transform: translateY(50%);
            display: flex;
            align-items: center;
            z-index: 999;
          }
          #micBtn {
            background: url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 24 24' fill='none' xmlns='http://www.w3.org/2000/svg'%3E%3Crect x='9' y='2' width='6' height='12' rx='3' fill='%23888'/%3E%3Cpath d='M5 10c0 3.866 3.134 7 7 7s7-3.134 7-7' stroke='%23888' stroke-width='2' stroke-linecap='round'/%3E%3Cline x1='12' y1='17' x2='12' y2='21' stroke='%23888' stroke-width='2' stroke-linecap='round'/%3E%3Cline x1='8' y1='21' x2='16' y2='21' stroke='%23888' stroke-width='2' stroke-linecap='round'/%3E%3C/svg%3E") no-repeat center;
            background-size: 24px;
            border: none;
            width: 32px;
            height: 32px;
            cursor: pointer;
            padding: 4px;
            border-radius: 50%;
            transition: background 0.15s, transform 0.1s;
            opacity: 0.7;
          }
          #micBtn:hover { background-color: rgba(142,68,173,0.12); opacity: 1; }
          #micBtn:active { transform: scale(0.9); }
          #micBtn.listening { 
            animation: micpulse 0.9s infinite; 
            background-color: rgba(231, 76, 60, 0.1);
            opacity: 1;
          }
          @keyframes micpulse {
            0%,100% { box-shadow: 0 0 0px #e74c3c; }
            50%      { box-shadow: 0 0 8px #e74c3c; }
          }
          #micStatus {
            font-size: 0.72rem;
            color: #8e44ad;
            margin-right: 4px;
            font-style: italic;
            white-space: nowrap;
          }
          #micStatus.active { color: #e74c3c; font-weight: 600; }
        `;
        parentDoc.head.appendChild(style);
      }

      // Ensure the chat input container has relative positioning so our absolute button aligns correctly
      chatInputContainer.style.position = 'relative';

      // Create the wrapper
      const wrap = parentDoc.createElement('div');
      wrap.id = 'micBtnWrap';

      const status = parentDoc.createElement('span');
      status.id = 'micStatus';

      const btn = parentDoc.createElement('button');
      btn.id = 'micBtn';
      btn.title = 'Click to speak / बोलने के लिए क्लिक करें';
      btn.setAttribute('aria-label', 'Toggle Voice Input');
      btn.textContent = '';

      wrap.appendChild(status);
      wrap.appendChild(btn);
      chatInputContainer.appendChild(wrap);

      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

      if (!SR) {
        btn.title = 'Speech not supported - use Chrome/Edge';
        btn.style.opacity = '0.35';
        btn.style.cursor  = 'not-allowed';
        return true;
      }

      const rec = new SR();
      rec.lang = speechLangCode;
      rec.interimResults = true;
      rec.maxAlternatives = 1;
      let listening = false;

      btn.addEventListener('click', () => { listening ? rec.stop() : rec.start(); });

      rec.onstart = () => {
        listening = true;
        btn.textContent = '';
        btn.classList.add('listening');
        status.textContent = '[LIVE]';
        status.classList.add('active');
        btn.setAttribute('aria-pressed', 'true');
      };

      rec.onresult = (e) => {
        let interim = '', final = '';
        for (let i = e.resultIndex; i < e.results.length; i++) {
          const tr = e.results[i][0].transcript;
          if (e.results[i].isFinal) final += tr; else interim += tr;
        }
        status.textContent = final || interim ? ' ' + (final || interim).slice(0,24) + '...' : '[LIVE]';
        if (final) {
          const ta = parentDoc.querySelector('textarea[data-testid="stChatInputTextArea"]');
          if (ta) {
            Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype,'value')
              .set.call(ta, final);
            ta.dispatchEvent(new Event('input', {bubbles:true}));
            setTimeout(() => ta.dispatchEvent(
              new KeyboardEvent('keydown', {key:'Enter',code:'Enter',keyCode:13,bubbles:true,cancelable:true})
            ), 550);
          }
        }
      };

      rec.onend = () => {
        listening = false;
        btn.textContent = '';
        btn.classList.remove('listening');
        status.textContent = '';
        status.classList.remove('active');
        btn.setAttribute('aria-pressed', 'false');
      };

      rec.onerror = (e) => {
        listening = false;
        btn.textContent = '';
        btn.classList.remove('listening');
        status.textContent = e.error === 'not-allowed' ? '' : 'Warning: ';
        status.classList.remove('active');
      };
      
      return true;
  }

  if (!inject()) {
    const interval = setInterval(() => {
      if (inject()) clearInterval(interval);
    }, 500);
    setTimeout(() => clearInterval(interval), 10000); // 10s max
  }
})();