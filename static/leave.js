const $ = id => document.getElementById(id);
const form = $('leaveForm');
const voiceBox = $('voiceBox');
const transcript = $('transcript');
const today = new Date();
const iso = date => `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
$('startDate').min = iso(today); $('endDate').min = iso(today);

function setPeriod(value) {
  const radio = document.querySelector(`input[name="period"][value="${value || '全天'}"]`);
  if (radio) radio.checked = true;
}

function fillForm(data) {
  if (data.leaveType) $('leaveType').value=data.leaveType;
  if (data.startDate) $('startDate').value=data.startDate;
  if (data.endDate) $('endDate').value=data.endDate;
  if (data.reason) $('reason').value=data.reason;
  setPeriod(data.period); updateSummary(); updateCount();
  document.querySelectorAll('.field').forEach((el,i)=>{el.animate([{opacity:.45,transform:'translateY(4px)'},{opacity:1,transform:'none'}],{duration:280,delay:i*35})});
}

async function parseSpeech(text) {
  $('voiceTitle').textContent='火山方舟正在解析…';
  try {
    const response=await fetch('/api/leave/parse',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
    if(!response.ok){const error=await response.json().catch(()=>({}));throw new Error(error.detail||'解析请求失败')}
    const data=await response.json();
    fillForm(data);
    $('voiceTitle').textContent='方舟解析完成，请确认信息';
  } catch (error) {
    $('voiceTitle').textContent='方舟解析失败，请重试';
    transcript.textContent=error.message;
  }
}

function updateSummary() {
  const start=$('startDate').value,end=$('endDate').value;
  if(!start||!end){$('duration').textContent='请完善日期';return}
  const days=Math.max(1,Math.round((new Date(end)-new Date(start))/86400000)+1);
  const period=document.querySelector('input[name="period"]:checked').value;
  $('duration').textContent=period==='全天'?`${days} 天`:'0.5 天';
  $('endDate').min=start;
}
function updateCount(){$('count').textContent=$('reason').value.length}
['startDate','endDate'].forEach(id=>$(id).addEventListener('change',updateSummary));
document.querySelectorAll('input[name="period"]').forEach(r=>r.addEventListener('change',updateSummary));
$('reason').addEventListener('input',updateCount);

const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;
if(Recognition){
  const recognition=new Recognition(); recognition.lang='zh-CN'; recognition.interimResults=true; recognition.continuous=true;
  let recording=false,manualStop=false,finalText='';
  recognition.onstart=()=>{voiceBox.classList.add('listening');$('voiceTitle').textContent='正在聆听，再次点击结束';if(!finalText)transcript.textContent='请自然地说出日期、类型和原因'};
  recognition.onresult=e=>{let interim='';for(let i=e.resultIndex;i<e.results.length;i++){const piece=e.results[i][0].transcript;if(e.results[i].isFinal)finalText+=piece;else interim+=piece}transcript.textContent=(finalText+interim).trim()||'请自然地说出日期、类型和原因'};
  recognition.onend=()=>{if(recording&&!manualStop){try{recognition.start()}catch{}return}voiceBox.classList.remove('listening');recording=false;const text=finalText.trim();if(manualStop&&text)parseSpeech(text);else if(manualStop){$('voiceTitle').textContent='没有听清，请重新说一遍';transcript.textContent='点击麦克风重新开始'}manualStop=false};
  recognition.onerror=e=>{if(e.error==='no-speech'&&recording)return;recording=false;manualStop=false;voiceBox.classList.remove('listening');$('voiceTitle').textContent='没有识别成功，请重试';transcript.textContent=e.error==='not-allowed'?'请在浏览器中允许麦克风权限':'也可以直接手动填写下方表单'};
  $('micBtn').addEventListener('click',()=>{if(recording){manualStop=true;recording=false;$('voiceTitle').textContent='语音结束，正在整理…';recognition.stop();return}finalText='';manualStop=false;recording=true;try{recognition.start()}catch{recording=false}});
}else{$('micBtn').disabled=true;$('voiceTitle').textContent='当前浏览器不支持语音输入';transcript.textContent='请使用 Chrome 或 Edge，或手动填写表单'}

form.addEventListener('submit',e=>{e.preventDefault();const start=$('startDate').value,end=$('endDate').value;if(end<start){$('endDate').setCustomValidity('结束日期不能早于开始日期');$('endDate').reportValidity();return}$('endDate').setCustomValidity('');form.style.display='none';$('success').style.display='block';$('successText').textContent=`${$('leaveType').value} · ${start} 至 ${end} · ${document.querySelector('input[name="period"]:checked').value}`});
$('againBtn').addEventListener('click',()=>{form.reset();form.style.display='grid';$('success').style.display='none';transcript.textContent='例如：下周一上午请半天年假，去办理证件';$('voiceTitle').textContent='点击麦克风，说出请假安排';updateSummary();updateCount()});
