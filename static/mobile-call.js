import { socketUrl, createPeer, microphone } from './call-core.js';

const $ = id => document.getElementById(id);
let deviceId = new URLSearchParams(location.search).get('device') || localStorage.phoneDeviceId;
if (!deviceId) {
  const randomId = globalThis.crypto?.randomUUID?.() || `${Date.now().toString(36)}${Math.random().toString(36).slice(2)}`;
  deviceId = 'phone-' + randomId.replaceAll('-', '').slice(0, 6);
  localStorage.phoneDeviceId = deviceId;
}
$('deviceId').textContent = deviceId;

let ws, pc, stream, caller, pendingOffer, tick, seconds = 0;
let pendingCandidates = [];
let captureContext, captureNode, captureSource, speechFrames = [], speaking = false, silentFrames = 0;
function connect() {
  ws = new WebSocket(socketUrl(deviceId));
  ws.onopen = () => { $('status').textContent = '等待来电'; $('dot').classList.add('online'); };
  ws.onclose = () => setTimeout(connect, 1500);
  ws.onmessage = async event => {
    const message = JSON.parse(event.data);
    if (message.type === 'offer') {
      caller = message.from; pendingOffer = message.sdp;
      $('caller').textContent = `${caller} 来电`;
      $('incoming').classList.add('show');
      navigator.vibrate?.([400, 250, 400]);
    }
    if (message.type === 'ice') {
      if (pc?.remoteDescription) await pc.addIceCandidate(message.candidate);
      else pendingCandidates.push(message.candidate);
    }
    if (message.type === 'hangup') end();
  };
}
connect();
function send(data) { ws.send(JSON.stringify({ ...data, target: caller })); }
$('accept').onclick = async () => {
  try {
    $('status').textContent = '正在启用麦克风…';
    stream = await microphone();
    pc = createPeer(candidate => send({ type: 'ice', candidate }), remote => $('remote').srcObject = remote);
    stream.getTracks().forEach(track => pc.addTrack(track, stream));
    await pc.setRemoteDescription(pendingOffer);
    for (const candidate of pendingCandidates.splice(0)) await pc.addIceCandidate(candidate);
    const answer = await pc.createAnswer(); await pc.setLocalDescription(answer);
    send({ type: 'answer', sdp: answer });
    $('incoming').classList.remove('show'); $('inCall').classList.add('show');
    $('caller').textContent = `正在与 ${caller} 通话`; startTimer(); startVoiceCapture();
  } catch (error) {
    const insecure = !window.isSecureContext;
    $('status').textContent = insecure ? '手机浏览器需要 HTTPS 才能接听' : '麦克风开启失败，请检查权限';
    $('timer').textContent = insecure ? '请使用 HTTPS 或安装 Android App' : (error?.message || '请允许麦克风权限');
  }
};
$('reject').onclick = () => { send({ type: 'reject' }); end(); };
$('hangup').onclick = () => { send({ type: 'hangup' }); end(); };
$('mute').onclick = () => { const track = stream?.getAudioTracks()[0]; if (track) { track.enabled = !track.enabled; $('mute').textContent = track.enabled ? '静音' : '取消静音'; } };
$('copy').onclick = async () => { await navigator.clipboard.writeText(deviceId); $('copy').textContent = '已复制'; };
function startTimer() { seconds = 0; tick = setInterval(() => $('timer').textContent = `${String(Math.floor(++seconds / 60)).padStart(2, '0')}:${String(seconds % 60).padStart(2, '0')}`, 1000); }
function startVoiceCapture() { captureContext = new AudioContext(); captureSource = captureContext.createMediaStreamSource(stream); captureNode = captureContext.createScriptProcessor(4096, 1, 1); captureNode.onaudioprocess = event => { const input = event.inputBuffer.getChannelData(0); let energy = 0; for (const value of input) energy += value * value; energy = Math.sqrt(energy / input.length); const ratio = captureContext.sampleRate / 16000; const pcm = new Int16Array(Math.floor(input.length / ratio)); for (let i = 0; i < pcm.length; i++) { const value = Math.max(-1, Math.min(1, input[Math.floor(i * ratio)])); pcm[i] = value < 0 ? value * 32768 : value * 32767; } if (energy > .018) { speaking = true; silentFrames = 0; speechFrames.push(new Uint8Array(pcm.buffer)); } else if (speaking) { speechFrames.push(new Uint8Array(pcm.buffer)); if (++silentFrames >= 5) flushSpeech(); } }; captureSource.connect(captureNode); captureNode.connect(captureContext.destination); }
function flushSpeech() { const length = speechFrames.reduce((sum, item) => sum + item.length, 0); if (length > 8000) { const joined = new Uint8Array(length); let offset = 0; for (const item of speechFrames) { joined.set(item, offset); offset += item.length; } let binary = ''; for (let i = 0; i < joined.length; i += 8192) binary += String.fromCharCode(...joined.subarray(i, i + 8192)); send({ type: 'customer_audio', audioBase64: btoa(binary) }); } speechFrames = []; speaking = false; silentFrames = 0; }
function end() { clearInterval(tick); captureNode?.disconnect(); captureSource?.disconnect(); captureContext?.close(); captureNode = null; captureContext = null; pc?.close(); stream?.getTracks().forEach(track => track.stop()); pc = null; stream = null; pendingCandidates = []; speechFrames = []; speaking = false; $('incoming').classList.remove('show'); $('inCall').classList.remove('show'); $('caller').textContent = '等待电脑呼叫'; $('timer').textContent = '保持应用在线'; }
