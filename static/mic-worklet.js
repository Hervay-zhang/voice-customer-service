class PcmCapture extends AudioWorkletProcessor {
  constructor(){super();this.pending=[];this.phase=0}
  process(inputs){const input=inputs[0]?.[0];if(!input)return true;const ratio=sampleRate/16000;for(let i=0;i<input.length;i++){this.phase++;if(this.phase>=ratio){this.phase-=ratio;const v=Math.max(-1,Math.min(1,input[i]));this.pending.push(v<0?v*32768:v*32767)}}while(this.pending.length>=320){const frame=new Int16Array(this.pending.splice(0,320));this.port.postMessage(frame.buffer,[frame.buffer])}return true}
}
registerProcessor('pcm-capture',PcmCapture);
