import { Amplify } from 'aws-amplify';
import { signIn, signOut, fetchAuthSession } from 'aws-amplify/auth';
import { SignatureV4 } from '@smithy/signature-v4';
import { Sha256 } from '@aws-crypto/sha256-js';

Amplify.configure({Auth:{Cognito:{userPoolId:'us-east-1_xuxlokqEr',userPoolClientId:'3g0912f70vs77d753jdnb7i1cm',identityPoolId:'us-east-1:24905ab4-2105-4f7a-88b6-4feeb223eaf3'}}});

const AGENT_ARN='arn:aws:bedrock-agentcore:us-east-1:463440883924:runtime/finops_runtime-f25c6ZCRzH';
const REGION='us-east-1';
let sessionId='s-'+Date.now();

window.doLogin=async()=>{
  const u=document.getElementById('emailInput').value,p=document.getElementById('passInput').value,err=document.getElementById('loginError');
  try{try{await signOut()}catch(e){}await signIn({username:u,password:p});document.getElementById('loginOverlay').style.display='none';loadAlerts()}
  catch(e){err.textContent=e.message;err.style.display='block'}
};

async function callAgent(prompt){
  document.getElementById('btn').disabled=true;
  document.getElementById('typing').classList.add('active');
  try{
    const session=await fetchAuthSession();
    const endpoint=`https://bedrock-agentcore.${REGION}.amazonaws.com`;
    const path=`/runtimes/${encodeURIComponent(AGENT_ARN)}/invocations`;
    const body=JSON.stringify({prompt,sessionId,userId:'console'});
    const signer=new SignatureV4({service:'bedrock-agentcore',region:REGION,credentials:session.credentials,sha256:Sha256});
    const signed=await signer.sign({method:'POST',hostname:`bedrock-agentcore.${REGION}.amazonaws.com`,path,headers:{'Content-Type':'application/json',host:`bedrock-agentcore.${REGION}.amazonaws.com`},body});
    const res=await fetch(endpoint+path,{method:'POST',headers:signed.headers,body});
    const data=await res.json();
    const text=data.result||data.response||JSON.stringify(data);
    renderResponse(text);
  }catch(e){renderResponse('Error: '+e.message)}
  document.getElementById('btn').disabled=false;
  document.getElementById('typing').classList.remove('active');
}

function renderResponse(text){
  const area=document.getElementById('chatArea');
  // Parse sections from markdown
  const sections=parseSections(text);
  let html='<div class="investigation-result">';
  
  if(sections.summary) html+=`<div class="result-summary">${sections.summary}</div>`;
  if(sections.findings.length) html+=`<div class="result-section"><h4>📊 Findings</h4><div class="findings-grid">${sections.findings.map(f=>`<div class="finding-card ${f.status||''}">${f.text}</div>`).join('')}</div></div>`;
  if(sections.rootCause) html+=`<div class="result-section"><h4>🔍 Root Cause</h4><p>${sections.rootCause}</p></div>`;
  if(sections.actions.length) html+=`<div class="result-section"><h4>⚡ Actions</h4><div class="action-buttons">${sections.actions.map(a=>`<button class="action-btn ${a.destructive?'destructive':''}" onclick="executeAction('${a.prompt}')">${a.label}</button>`).join('')}</div></div>`;
  if(sections.timeline.length) html+=`<div class="result-section"><h4>📅 Timeline</h4><div class="timeline">${sections.timeline.map(t=>`<div class="timeline-item"><span class="tl-time">${t.time}</span><span class="tl-event">${t.event}</span></div>`).join('')}</div></div>`;
  if(sections.raw) html+=`<div class="result-section raw-response">${formatMd(sections.raw)}</div>`;
  
  html+='</div>';
  area.innerHTML=html;
  area.scrollTop=0;
}

function parseSections(text){
  const sections={summary:'',findings:[],rootCause:'',actions:[],timeline:[],raw:''};
  
  // Try to extract structured parts
  const lines=text.split('\n');
  let currentSection='raw';
  let rawLines=[];
  
  for(const line of lines){
    const lower=line.toLowerCase();
    if(lower.includes('root cause')||lower.includes('culprit')){currentSection='rootCause';sections.rootCause+=line.replace(/^#+\s*/,'').replace(/\*\*/g,'')+' ';continue}
    if(lower.includes('recommend')||lower.includes('action')||lower.includes('immediate')){currentSection='actions'}
    if(lower.includes('timeline')||lower.match(/\d{1,2}:\d{2}/)){
      const timeMatch=line.match(/(\d{1,2}:\d{2}[^:]*?)[:—-]\s*(.+)/);
      if(timeMatch){sections.timeline.push({time:timeMatch[1].trim(),event:timeMatch[2].trim()});continue}
    }
    if(lower.includes('cost impact')||lower.includes('burn rate')||lower.includes('$/day')||lower.includes('$/hour')){
      sections.findings.push({text:line.replace(/^[-*•]\s*/,'').replace(/\*\*/g,''),status:'danger'});continue}
    rawLines.push(line);
  }
  
  // Extract summary (first meaningful paragraph)
  const firstPara=rawLines.find(l=>l.length>30&&!l.startsWith('#')&&!l.startsWith('|'));
  if(firstPara)sections.summary=firstPara.replace(/\*\*/g,'');
  
  // Add default actions
  sections.actions=[
    {label:'📧 Notify Owner',prompt:'Send a notification to the owner summarizing what you found',destructive:false},
    {label:'💰 Set Budget',prompt:'Set a budget alert at $100/month for Bedrock',destructive:false},
    {label:'🛑 Stop Runaway Agent',prompt:'Stop the agent that is causing the spike. Ask me which one first.',destructive:true}
  ];
  
  sections.raw=rawLines.join('\n');
  return sections;
}

function formatMd(text){return text.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/^## (.*)/gm,'<h3>$1</h3>').replace(/^### (.*)/gm,'<h4>$1</h4>')}

window.executeAction=async(prompt)=>{
  const area=document.getElementById('chatArea');
  area.innerHTML+=`<div class="msg user"><div class="bubble">${prompt}</div></div>`;
  await callAgent(prompt);
};

// Load live alerts from CloudWatch
async function loadAlerts(){
  const alertList=document.getElementById('alertList');
  alertList.innerHTML='<div style="padding:16px;color:#9CA3AF;font-size:12px">Loading alerts...</div>';
  try{
    // Call agent to get alarm status
    const session=await fetchAuthSession();
    const endpoint=`https://bedrock-agentcore.${REGION}.amazonaws.com`;
    const path=`/runtimes/${encodeURIComponent(AGENT_ARN)}/invocations`;
    const body=JSON.stringify({prompt:'Call get_alarm_status and return ONLY the raw JSON result. No explanation.',sessionId:'alerts-'+Date.now(),userId:'system'});
    const signer=new SignatureV4({service:'bedrock-agentcore',region:REGION,credentials:session.credentials,sha256:Sha256});
    const signed=await signer.sign({method:'POST',hostname:`bedrock-agentcore.${REGION}.amazonaws.com`,path,headers:{'Content-Type':'application/json',host:`bedrock-agentcore.${REGION}.amazonaws.com`},body});
    const res=await fetch(endpoint+path,{method:'POST',headers:signed.headers,body});
    const data=await res.json();
    const text=data.result||data.response||'';
    
    // Try to parse alarms from response
    try{
      const jsonMatch=text.match(/\[[\s\S]*\]/);
      if(jsonMatch){
        const alarms=JSON.parse(jsonMatch[0]);
        alertList.innerHTML=alarms.map(a=>{
          const sev=a.state==='ALARM'?'critical':a.state==='INSUFFICIENT_DATA'?'warning':'info';
          return `<div class="alert-item" onclick="investigateAlert('${a.name}')"><div class="title"><span class="severity ${sev}"></span>${a.name}</div><div class="meta">${a.metric||''} • ${a.state}</div></div>`;
        }).join('')||'<div style="padding:16px;color:#10B981;font-size:12px">✅ No active alarms</div>';
        return;
      }
    }catch(e){}
    
    // Fallback: show static alerts
    alertList.innerHTML=`<div class="alert-item" onclick="investigateAlert('Bedrock token usage')"><div class="title"><span class="severity warning"></span>Bedrock Usage Monitor</div><div class="meta">Click to check current status</div></div>`;
  }catch(e){
    alertList.innerHTML='<div style="padding:16px;color:#EF4444;font-size:12px">Failed to load alerts</div>';
  }
}

window.investigateAlert=(name)=>{
  document.getElementById('chatArea').innerHTML='<div style="padding:20px;color:#6B7280">Investigating...</div>';
  document.getElementById('typing').classList.add('active');
  callAgent(`Investigate alert: "${name}". Use get_alarm_status, get_bedrock_usage, get_recent_changes, get_recent_deployments. Provide: summary, findings with numbers, root cause, timeline, and recommended actions.`);
};

window.newChat=()=>{sessionId='s-'+Date.now();document.getElementById('chatArea').innerHTML='<div class="empty-state"><h3>Ask anything</h3><p>Costs, agents, anomalies, actions</p></div>'};
window.send=()=>{const input=document.getElementById('input');const msg=input.value.trim();if(!msg)return;input.value='';document.getElementById('chatArea').innerHTML=`<div class="msg user"><div class="bubble">${msg}</div></div>`;callAgent(msg)};
