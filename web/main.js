import { Amplify } from 'aws-amplify';
import { signIn, signOut, fetchAuthSession } from 'aws-amplify/auth';
import { SignatureV4 } from '@smithy/signature-v4';
import { Sha256 } from '@aws-crypto/sha256-js';

Amplify.configure({Auth:{Cognito:{userPoolId:'us-east-1_xuxlokqEr',userPoolClientId:'3g0912f70vs77d753jdnb7i1cm',identityPoolId:'us-east-1:24905ab4-2105-4f7a-88b6-4feeb223eaf3'}}});

const AGENT_ARN='arn:aws:bedrock-agentcore:us-east-1:463440883924:runtime/finops_runtime-f25c6ZCRzH';
const REGION='us-east-1';
let sessionId='s-'+Date.now();

// --- AUTH ---
window.doLogin=async()=>{
  const u=document.getElementById('emailInput').value,p=document.getElementById('passInput').value,err=document.getElementById('loginError');
  try{try{await signOut()}catch(e){}await signIn({username:u,password:p});document.getElementById('loginOverlay').style.display='none';loadAlerts()}
  catch(e){err.textContent=e.message;err.style.display='block'}
};

// --- AGENT CALL ---
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
    addMsg(data.result||data.response||JSON.stringify(data),'agent');
  }catch(e){addMsg('Error: '+e.message,'agent')}
  document.getElementById('btn').disabled=false;
  document.getElementById('typing').classList.remove('active');
}

// --- ALERTS (direct CloudWatch, fast) ---
async function loadAlerts(){
  const alertList=document.getElementById('alertList');
  alertList.innerHTML='<div style="padding:12px;color:#9CA3AF;font-size:11px">Loading...</div>';
  try{
    const session=await fetchAuthSession();
    const signer=new SignatureV4({service:'monitoring',region:REGION,credentials:session.credentials,sha256:Sha256});
    
    // Current states
    const b1='Action=DescribeAlarms&Version=2010-08-01&AlarmNamePrefix=CostAgent';
    const s1=await signer.sign({method:'POST',hostname:`monitoring.${REGION}.amazonaws.com`,path:'/',headers:{'Content-Type':'application/x-www-form-urlencoded',host:`monitoring.${REGION}.amazonaws.com`},body:b1});
    const r1=await fetch(`https://monitoring.${REGION}.amazonaws.com/`,{method:'POST',headers:s1.headers,body:b1});
    const x1=await r1.text();
    const curNames=[...x1.matchAll(/<AlarmName>(.*?)<\/AlarmName>/g)];
    const curStates=[...x1.matchAll(/<StateValue>(.*?)<\/StateValue>/g)];

    // History (last 3 days)
    const start=new Date(Date.now()-86400000*3).toISOString();
    const b2=`Action=DescribeAlarmHistory&Version=2010-08-01&HistoryItemType=StateUpdate&StartDate=${start}&MaxRecords=100`;
    const s2=await signer.sign({method:'POST',hostname:`monitoring.${REGION}.amazonaws.com`,path:'/',headers:{'Content-Type':'application/x-www-form-urlencoded',host:`monitoring.${REGION}.amazonaws.com`},body:b2});
    const r2=await fetch(`https://monitoring.${REGION}.amazonaws.com/`,{method:'POST',headers:s2.headers,body:b2});
    const x2=await r2.text();
    const hNames=[...x2.matchAll(/<AlarmName>(.*?)<\/AlarmName>/g)];
    const hTimes=[...x2.matchAll(/<Timestamp>(.*?)<\/Timestamp>/g)];
    const hSummaries=[...x2.matchAll(/<HistorySummary>(.*?)<\/HistorySummary>/g)];

    // Filter + group by date
    const byDate={};
    hNames.forEach((n,i)=>{
      if(!n[1].startsWith('CostAgent'))return;
      const ts=hTimes[i]?new Date(hTimes[i][1]):new Date();
      const sum=hSummaries[i]?hSummaries[i][1]:'';
      const isAlarm=sum.includes('to ALARM');
      const dateKey=ts.toLocaleDateString('en-US',{month:'short',day:'numeric'});
      if(!byDate[dateKey])byDate[dateKey]=[];
      byDate[dateKey].push({name:n[1],label:n[1].replace('CostAgent-',''),time:ts.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}),isAlarm});
    });

    let html='';
    // Current Status
    const live=curNames.filter((_,i)=>curStates[i]&&curStates[i][1]==='ALARM');
    html+=`<div class="section-label">Current Status</div>`;
    if(live.length){
      html+=live.map(a=>`<div class="alert-item" onclick="investigateAlert('${a[1]}')"><div class="title"><span class="severity critical"></span>${a[1].replace('CostAgent-','')}</div><div class="meta">🔴 ALARM — click to investigate</div></div>`).join('');
    }else{
      html+=`<div style="padding:8px 14px;font-size:12px;color:#10B981">✅ All Clear</div>`;
    }

    // Split today vs past days
    const todayKey=new Date().toLocaleDateString('en-US',{month:'short',day:'numeric'});
    const todayEvents=byDate[todayKey]||[];
    const pastDates=Object.entries(byDate).filter(([k])=>k!==todayKey);

    // Recent (today's events)
    if(todayEvents.length){
      const spikes=todayEvents.filter(e=>e.isAlarm).length;
      html+=`<div class="section-label">Recent <span style="color:#DC2626;font-size:9px;margin-left:4px">${spikes} spike${spikes!==1?'s':''} today</span></div>`;
      const byAlarm={};
      todayEvents.forEach(e=>{if(!byAlarm[e.label])byAlarm[e.label]=[];byAlarm[e.label].push(e)});
      Object.entries(byAlarm).forEach(([label,alarmEvents])=>{
        const fires=alarmEvents.filter(e=>e.isAlarm).length;
        if(!fires)return;
        html+=`<div class="alert-item tree-parent" onclick="const c=this.querySelector('.tree-children');if(c)c.classList.toggle('hidden');investigateAlert('${alarmEvents[0].name}')">`;
        html+=`<div class="title"><span class="severity critical"></span>${label} <span style="font-size:10px;color:#DC2626;font-weight:400">(${fires}x)</span></div>`;
        html+=`<div class="meta">${alarmEvents[0].time} — ${alarmEvents[alarmEvents.length-1].time}</div>`;
        if(alarmEvents.length>1){
          html+=`<div class="tree-children hidden" onclick="event.stopPropagation()">`;
          alarmEvents.forEach(e=>{html+=`<div class="tree-child">${e.time} ${e.isAlarm?'🔴 Fired':'✅ Resolved'}</div>`});
          html+=`</div>`;
        }
        html+=`</div>`;
      });
    }

    // Past days
    pastDates.forEach(([date,events])=>{
      const spikes=events.filter(e=>e.isAlarm).length;
      html+=`<div class="section-label date-tab" onclick="this.nextElementSibling.classList.toggle('hidden')" style="cursor:pointer">📅 ${date} <span style="color:#DC2626;font-size:9px;margin-left:4px">${spikes} spike${spikes!==1?'s':''}</span></div>`;
      html+=`<div class="date-events">`;
      const byAlarm={};
      events.forEach(e=>{if(!byAlarm[e.label])byAlarm[e.label]=[];byAlarm[e.label].push(e)});
      Object.entries(byAlarm).forEach(([label,alarmEvents])=>{
        const fires=alarmEvents.filter(e=>e.isAlarm).length;
        if(!fires)return;
        html+=`<div class="alert-item" onclick="investigateAlert('${alarmEvents[0].name}')"><div class="title"><span class="severity warning"></span>${label} (${fires}x)</div><div class="meta">${alarmEvents[0].time}</div></div>`;
      });
      html+=`</div>`;
    });

    alertList.innerHTML=html||'<div style="padding:12px;color:#9CA3AF;font-size:11px">No data</div>';
  }catch(e){alertList.innerHTML='<div style="padding:12px;color:#EF4444;font-size:11px">'+e.message+'</div>'}
}

// --- UI ---
window.investigateAlert=(name)=>{
  const area=document.getElementById('chatArea');
  const empty=area.querySelector('.empty-state');if(empty)empty.remove();
  addMsg(`Investigate: ${name.replace('CostAgent-','')}`,'user');
  callAgent(`Investigate alarm "${name}". You are a cost forensics investigator. Be SPECIFIC:

**STATUS:** Is it firing now or resolved? One sentence.
**IMPACT:** Exact $/hour and $/day. Compare to normal baseline.
**WHO:** Which specific agent ARN, Lambda function, or IAM role is responsible? Check CloudTrail.
**WHAT CHANGED:** What deployment or config change triggered this? Give commit time + user.
**ROOT CAUSE:** One sentence — not "high usage" but WHY (loop? prompt change? new workload?)
**FIX:** One specific command or action to stop it. Not "monitor" — give me the fix.

If you can't identify WHO, say what's blocking you (e.g. "invocation logging not enabled").
Do NOT say "monitor" or "investigate further" — give a definitive answer.`);
};

window.newChat=()=>{sessionId='s-'+Date.now();document.getElementById('chatArea').innerHTML='<div class="empty-state"><h3>Ask anything</h3><p>Costs, agents, anomalies, actions</p></div>'};

window.send=()=>{
  const input=document.getElementById('input');const msg=input.value.trim();if(!msg)return;input.value='';
  const area=document.getElementById('chatArea');const empty=area.querySelector('.empty-state');if(empty)empty.remove();
  addMsg(msg,'user');callAgent(msg);
};

window.executeAction=async(prompt)=>{addMsg(prompt,'user');callAgent(prompt)};

function addMsg(text,role){
  const area=document.getElementById('chatArea');
  const div=document.createElement('div');div.className='msg '+role;
  if(role==='agent'){
    const fmt=text.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br>').replace(/`([^`]+)`/g,'<code>$1</code>');
    div.innerHTML=`<div class="bubble"><div class="raw-response">${fmt}</div><div class="action-buttons"><button class="action-btn" onclick="executeAction('Send notification to owner summarizing findings')">📧 Notify</button><button class="action-btn" onclick="executeAction('Set budget alert at $100/month for Bedrock')">💰 Budget</button><button class="action-btn destructive" onclick="executeAction('What should I stop to reduce costs? Show options first.')">🛑 Stop</button></div></div>`;
  }else{
    div.innerHTML=`<div class="bubble">${text}</div>`;
  }
  area.appendChild(div);area.scrollTop=area.scrollHeight;
}
