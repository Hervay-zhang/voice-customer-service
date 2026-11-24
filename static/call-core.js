export function socketUrl(clientId){const scheme=location.protocol==='https:'?'wss':'ws';return `${scheme}://${location.host}/api/calls/ws/${encodeURIComponent(clientId)}`}
export function iceServers(){return [{urls:'stun:stun.l.google.com:19302'}]}
export function createPeer(onIce,onTrack){const pc=new RTCPeerConnection({iceServers:iceServers()});pc.onicecandidate=e=>e.candidate&&onIce(e.candidate);pc.ontrack=e=>onTrack(e.streams[0]);return pc}
export async function microphone(){return navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,autoGainControl:true},video:false})}
