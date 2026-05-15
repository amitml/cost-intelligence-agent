import { Amplify } from 'aws-amplify';
import { signIn, signOut, fetchAuthSession } from 'aws-amplify/auth';
import { SignatureV4 } from '@smithy/signature-v4';
import { Sha256 } from '@aws-crypto/sha256-js';

Amplify.configure({
  Auth: {
    Cognito: {
      userPoolId: 'us-east-1_xuxlokqEr',
      userPoolClientId: '3g0912f70vs77d753jdnb7i1cm',
      identityPoolId: 'us-east-1:24905ab4-2105-4f7a-88b6-4feeb223eaf3'
    }
  }
});

const AGENT_ARN = 'arn:aws:bedrock-agentcore:us-east-1:463440883924:runtime/finops_runtime-f25c6ZCRzH';
const REGION = 'us-east-1';
let sessionId = 's-' + Date.now();

// Login
window.doLogin = async () => {
  const u = document.getElementById('emailInput').value;
  const p = document.getElementById('passInput').value;
  const err = document.getElementById('loginError');
  try {
    try { await signOut(); } catch(e) {}
    await signIn({ username: u, password: p });
    document.getElementById('loginOverlay').style.display = 'none';
  } catch (e) {
    err.textContent = e.message;
    err.style.display = 'block';
  }
};

// Call AgentCore directly
async function callAgent(prompt) {
  document.getElementById('btn').disabled = true;
  document.getElementById('typing').classList.add('active');

  try {
    const session = await fetchAuthSession();
    const creds = session.credentials;

    const endpoint = `https://bedrock-agentcore.${REGION}.amazonaws.com`;
    const path = `/runtimes/${encodeURIComponent(AGENT_ARN)}/invocations`;
    const body = JSON.stringify({ prompt, sessionId, userId: 'console' });

    const signer = new SignatureV4({
      service: 'bedrock-agentcore',
      region: REGION,
      credentials: creds,
      sha256: Sha256
    });

    const signed = await signer.sign({
      method: 'POST',
      hostname: `bedrock-agentcore.${REGION}.amazonaws.com`,
      path,
      headers: { 'Content-Type': 'application/json', host: `bedrock-agentcore.${REGION}.amazonaws.com` },
      body
    });

    const res = await fetch(endpoint + path, { method: 'POST', headers: signed.headers, body });
    const data = await res.json();
    addMsg(data.result || data.response || JSON.stringify(data), 'agent');
  } catch (e) {
    addMsg('Error: ' + e.message, 'agent');
  }

  document.getElementById('btn').disabled = false;
  document.getElementById('typing').classList.remove('active');
}

// UI
const alerts = [
  { id: 'a1', sev: 'critical', title: 'Bedrock InputTokens > 200K/5min', detail: 'Token spike', time: '2 min ago' },
  { id: 'a2', sev: 'warning', title: 'RPM > 100/min', detail: 'order-processing Lambda', time: '15 min ago' },
  { id: 'a3', sev: 'info', title: 'TPM Quota at 82%', detail: 'Approaching throttle', time: '1 hour ago' },
];

window.investigate = (id) => {
  const a = alerts.find(x => x.id === id);
  document.getElementById('chatArea').innerHTML = '';
  const q = `Investigate: "${a.title}" — ${a.detail}. Check real-time metrics, what changed, and recommend action.`;
  addMsg(q, 'user');
  callAgent(q);
};

window.newChat = () => { sessionId = 's-' + Date.now(); document.getElementById('chatArea').innerHTML = ''; };

window.send = () => {
  const input = document.getElementById('input');
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  addMsg(msg, 'user');
  callAgent(msg);
};

function addMsg(text, role) {
  const area = document.getElementById('chatArea');
  const empty = area.querySelector('.empty-state');
  if (empty) empty.remove();
  const d = document.createElement('div');
  d.className = 'msg ' + role;
  const f = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>').replace(/\n/g, '<br>').replace(/`([^`]+)`/g, '<code>$1</code>');
  d.innerHTML = `<div class="bubble">${f}</div>`;
  area.appendChild(d);
  area.scrollTop = area.scrollHeight;
}

// Render alerts
document.getElementById('alertList').innerHTML = alerts.map(a =>
  `<div class="alert-item" onclick="investigate('${a.id}')"><div class="title"><span class="severity ${a.sev}"></span>${a.title}</div><div class="meta">${a.detail} • ${a.time}</div></div>`
).join('');
