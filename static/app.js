const $ = (id) => document.getElementById(id);
const messagesEl = $('messages');
const input = $('input');
const form = $('chatForm');
const micBtn = $('micBtn');
const orb = $('orb');
const soundToggle = $('soundToggle');
const STORAGE_KEY = 'yunsheng-chat-history-v1';
let history = [];
let speakingEnabled = true;
let busy = false;

function saveHistory() {
  history = history.slice(-30);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
}

function restoreHistory() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
    if (!Array.isArray(saved) || !saved.length) return;
    history = saved
      .filter(item => item && ['user', 'assistant'].includes(item.role) && typeof item.content === 'string')
      .slice(-30);
    if (!history.length) return;
    messagesEl.innerHTML = '';
    history.forEach(item => addMessage(item.role, item.content));
    $('suggestions').style.display = 'none';
  } catch (_) {
    localStorage.removeItem(STORAGE_KEY);
  }
}

fetch('/api/config').then(r => r.json()).then(config => {
  $('companyName').textContent = config.companyName;
  $('serviceName').textContent = config.serviceName;
  if (!config.configured) $('hint').textContent = '尚未配置火山方舟，请复制 .env.example 为 .env 并填写密钥';
});

function addMessage(role, text) {
  const row = document.createElement('div');
  row.className = `message ${role}`;
  if (role === 'assistant') {
    const avatar = document.createElement('span'); avatar.className = 'mini-avatar'; avatar.textContent = '云'; row.appendChild(avatar);
  }
  const bubble = document.createElement('div'); bubble.className = 'bubble';
  const p = document.createElement('p'); p.textContent = text;
  const time = document.createElement('time'); time.textContent = new Date().toLocaleTimeString('zh-CN', {hour:'2-digit', minute:'2-digit'});
  bubble.append(p, time); row.appendChild(bubble); messagesEl.appendChild(row);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return p;
}

restoreHistory();

async function sendMessage(text) {
  text = text.trim(); if (!text || busy) return;
  busy = true; $('sendBtn').disabled = true; $('suggestions').style.display = 'none';
  addMessage('user', text); history.push({role:'user', content:text}); saveHistory(); input.value = ''; input.style.height = 'auto';
  const replyEl = addMessage('assistant', ''); let reply = ''; orb.className = 'orb thinking';
  try {
    const response = await fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({messages:history})});
    if (!response.ok) { const e = await response.json(); throw new Error(e.detail || '请求失败'); }
    const reader = response.body.getReader(); const decoder = new TextDecoder(); let buffer = '';
    while (true) {
      const {value, done} = await reader.read(); if (done) break;
      buffer += decoder.decode(value, {stream:true}); const lines = buffer.split('\n'); buffer = lines.pop();
      for (const line of lines) if (line) { const data = JSON.parse(line); if (data.error) throw new Error(data.error); reply += data.text || ''; replyEl.textContent = reply; messagesEl.scrollTop = messagesEl.scrollHeight; }
    }
    history.push({role:'assistant', content:reply}); saveHistory(); if (speakingEnabled && reply) speak(reply);
  } catch (error) { replyEl.textContent = `抱歉，服务暂时不可用。${error.message}`; }
  finally { busy = false; $('sendBtn').disabled = false; orb.className = 'orb'; input.focus(); }
}

form.addEventListener('submit', e => {e.preventDefault(); sendMessage(input.value)});
input.addEventListener('keydown', e => {if(e.key === 'Enter' && !e.shiftKey){e.preventDefault(); form.requestSubmit()}});
input.addEventListener('input', () => {input.style.height='auto'; input.style.height=Math.min(input.scrollHeight,96)+'px'});
document.querySelectorAll('.suggestions button').forEach(btn => btn.addEventListener('click', () => sendMessage(btn.textContent)));
$('clearBtn').addEventListener('click', () => {history=[]; localStorage.removeItem(STORAGE_KEY); messagesEl.innerHTML=''; addMessage('assistant','你好！新对话已经开始，请问有什么可以帮你？'); $('suggestions').style.display='flex'; speechSynthesis.cancel()});

function speak(text){ speechSynthesis.cancel(); const utterance = new SpeechSynthesisUtterance(text); utterance.lang='zh-CN'; utterance.rate=.95; speechSynthesis.speak(utterance); }
soundToggle.addEventListener('click', () => {speakingEnabled=!speakingEnabled; soundToggle.textContent=speakingEnabled?'◕':'○'; soundToggle.title=speakingEnabled?'语音播报已开启':'语音播报已关闭'; if(!speakingEnabled)speechSynthesis.cancel()});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
  const recognition = new SpeechRecognition(); recognition.lang='zh-CN'; recognition.interimResults=true;
  recognition.onstart=()=>{micBtn.classList.add('recording'); orb.className='orb listening'; $('hint').textContent='正在聆听，请说话…'};
  recognition.onresult=e=>{let text=''; for(let i=e.resultIndex;i<e.results.length;i++) text+=e.results[i][0].transcript; input.value=text};
  recognition.onend=()=>{micBtn.classList.remove('recording'); orb.className='orb'; $('hint').textContent='已完成语音输入，确认后即可发送'};
  recognition.onerror=e=>{$('hint').textContent=`语音识别失败：${e.error}`};
  micBtn.addEventListener('click',()=>recognition.start());
} else { micBtn.disabled=true; $('hint').textContent='当前浏览器不支持语音识别，请使用 Chrome 或 Edge'; }
