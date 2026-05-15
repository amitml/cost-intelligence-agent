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
  const formatted=text
    .replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>')
    .replace(/\n/g,'<br>')
    .replace(/`([^`]+)`/g,'<code>$1</code>')
    .replace(/^- /gm,'• ');
  
  const div=document.createElement('div');
  div.className='msg agent';
  div.innerHTML=`
    <div class="bubble" style="max-width:90%">
      <div class="raw-response">${formatted}</div>
      <div class="action-buttons" style="margin-top:12px">
        <button class="action-btn" onclick="executeAction('Send a notification to the owner with a 2-sentence summary of what you just found')">📧 Notify</button>
        <button class="action-btn" onclick="executeAction('Set a budget alert at $100/month for Bedrock')">💰 Budget</button>
        <button class="action-btn destructive" onclick="executeAction('What Lambda function should I stop to reduce costs? Show me options.')">🛑 Stop</button>
      </div>
    </div>`;
  area.appendChild(div);
  area.scrollTop=area.scrollHeight;
}

window.executeAction=async(prompt)=>{
  const area=document.getElementById('chatArea');
  area.innerHTML+=`<div class="msg user"><div class="bubble">${prompt}</div></div>`;
  await callAgent(prompt);
};

// Load live alerts from CloudWatch
async function loadAlerts(){
  const alertList=document.getElementById('alertList');
  alertList.innerHTML='<div style="padding:16px;color:#9CA3AF;font-size:12px">Loading...</div>';
  try{
    const session=await fetchAuthSession();
    const signer=new SignatureV4({service:'monitoring',region:REGION,credentials:session.credentials,sha256:Sha256});
    
    // Get current alarm states
    const body1='Action=DescribeAlarms&Version=2010-08-01&AlarmNamePrefix=CostAgent';
    const signed1=await signer.sign({method:'POST',hostname:`monitoring.${REGION}.amazonaws.com`,path:'/',headers:{'Content-Type':'application/x-www-form-urlencoded',host:`monitoring.${REGION}.amazonaws.com`},body:body1});
    const res1=await fetch(`https://monitoring.${REGION}.amazonaws.com/`,{method:'POST',headers:signed1.headers,body:body1});
    const xml1=await res1.text();
    const names=[...xml1.matchAll(/<AlarmName>(.*?)<\/AlarmName>/g)];
    const states=[...xml1.matchAll(/<StateValue>(.*?)<\/StateValue>/g)];
    
    // Get alarm history (state changes)
    const startDate=new Date(Date.now()-86400000*2).toISOString();
    const body2=`Action=DescribeAlarmHistory&Version=2010-08-01&AlarmNamePrefix=CostAgent&HistoryItemType=StateUpdate&StartDate=${startDate}`;
    const signed2=await signer.sign({method:'POST',hostname:`monitoring.${REGION}.amazonaws.com`,path:'/',headers:{'Content-Type':'application/x-www-form-urlencoded',host:`monitoring.${REGION}.amazonaws.com`},body:body2});
    const res2=await fetch(`https://monitoring.${REGION}.amazonaws.com/`,{method:'POST',headers:signed2.headers,body:body2});
    const xml2=await res2.text();
    const histNames=[...xml2.matchAll(/<AlarmName>(.*?)<\/AlarmName>/g)];
    const histTimes=[...xml2.matchAll(/<Timestamp>(.*?)<\/Timestamp>/g)];
    const histSummaries=[...xml2.matchAll(/<HistorySummary>(.*?)<\/HistorySummary>/g)];
    
    let html='';
    
    // Live section
    const alarming=names.filter((_,i)=>states[i]&&states[i][1]==='ALARM');
    if(alarming.length){
      html+=`<div class="section-label">🔴 Live</div>`;
      html+=alarming.map(a=>`<div class="alert-item" onclick="investigateAlert('${a[1]}')"><div class="title"><span class="severity critical"></span>${a[1].replace('CostAgent-','')}</div><div class="meta">ALARM — click to investigate</div></div>`).join('');
    }else{
      html+=`<div class="section-label" style="color:#10B981">✅ All Clear Now</div>`;
    }
    
    // History by day
    const today=new Date().toDateString();
    const yesterday=new Date(Date.now()-86400000).toDateString();
    const todayEvents=[];
    const yesterdayEvents=[];
    
    histNames.forEach((n,i)=>{
      const ts=histTimes[i]?new Date(histTimes[i][1]):new Date();
      const summary=histSummaries[i]?histSummaries[i][1]:'';
      const isAlarm=summary.includes('ALARM');
      const entry={name:n[1].replace('CostAgent-',''),fullName:n[1],time:ts.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}),isAlarm};
      if(ts.toDateString()===today)todayEvents.push(entry);
      else if(ts.toDateString()===yesterday)yesterdayEvents.push(entry);
    });
    
    if(todayEvents.length){
      html+=`<div class="section-label">📅 Today</div>`;
      html+=todayEvents.map(e=>`<div class="alert-item" onclick="investigateAlert('${e.fullName}')"><div class="title"><span class="severity ${e.isAlarm?'critical':'info'}"></span>${e.name}</div><div class="meta">${e.time} • ${e.isAlarm?'🔴 Fired':'✅ Resolved'}</div></div>`).join('');
    }
    
    if(yesterdayEvents.length){
      html+=`<div class="section-label">📅 Yesterday</div>`;
      html+=yesterdayEvents.map(e=>`<div class="alert-item" onclick="investigateAlert('${e.fullName}')"><div class="title"><span class="severity ${e.isAlarm?'warning':'info'}"></span>${e.name}</div><div class="meta">${e.time} • ${e.isAlarm?'🟡 Fired':'✅ Resolved'}</div></div>`).join('');
    }
    
    if(!todayEvents.length&&!yesterdayEvents.length){
      html+=`<div class="section-label">📋 History</div><div style="padding:8px 14px;font-size:11px;color:#9CA3AF">No alarm state changes in last 48h</div>`;
    }
    
    alertList.innerHTML=html;
  }catch(e){alertList.innerHTML='<div style="padding:16px;color:#9CA3AF;font-size:12px">Could not load</div>'}
}

window.investigateAlert=(name)=>{
  const area=document.getElementById('chatArea');
  const empty=area.querySelector('.empty-state');if(empty)empty.remove();
  const div=document.createElement('div');div.className='msg user';
  div.innerHTML=`<div class="bubble">Investigate: ${name}</div>`;
  area.appendChild(div);
  document.getElementById('typing').classList.add('active');
  callAgent(`Investigate alarm "${name}". 

RESPOND IN THIS EXACT FORMAT (no other text):

**STATUS:** [ALARM/OK] - one sentence what's happening
**IMPACT:** $X/hour or $X/day burn rate
**CAUSE:** one sentence root cause
**TIMELINE:**
- HH:MM — event
- HH:MM — event
**ACTION:** one specific thing to do right now

Keep it SHORT. Max 10 lines total.`);
};

window.newChat=()=>{sessionId='s-'+Date.now();document.getElementById('chatArea').innerHTML='<div class="empty-state"><h3>Ask anything</h3><p>Costs, agents, anomalies, actions</p></div>'};
window.send=()=>{const input=document.getElementById('input');const msg=input.value.trim();if(!msg)return;input.value='';const area=document.getElementById('chatArea');const empty=area.querySelector('.empty-state');if(empty)empty.remove();const div=document.createElement('div');div.className='msg user';div.innerHTML=`<div class="bubble">${msg}</div>`;area.appendChild(div);area.scrollTop=area.scrollHeight;callAgent(msg)};
