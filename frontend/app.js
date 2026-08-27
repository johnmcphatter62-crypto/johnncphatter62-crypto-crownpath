const output=document.querySelector('#output');
const guide=document.querySelector('#guide');
const loginMessage=document.querySelector('#loginMessage');
const registerMessage=document.querySelector('#registerMessage');
const ownerMessage=document.querySelector('#ownerMessage');
const sessionCard=document.querySelector('#sessionCard');
const ownerActivation=document.querySelector('#ownerActivation');
const ownerPanel=document.querySelector('#ownerPanel');
const ownerPanelMessage=document.querySelector('#ownerPanelMessage');
const userList=document.querySelector('#userList');

async function jsonRequest(url,options={}){
  const response=await fetch(url,{...options,headers:{'Content-Type':'application/json',...(options.headers||{})}});
  let data={};
  try{data=await response.json()}catch(_){data={}}
  if(!response.ok) throw new Error(data.detail||'CrownPath request could not be completed.');
  return data;
}

async function showHealth(){
  try{output.textContent=JSON.stringify(await jsonRequest('/api/health'),null,2)}
  catch(e){output.textContent='CrownPath health check unavailable: '+e.message}
}

function showSession(user){
  sessionCard.hidden=false;
  document.querySelector('#sessionName').textContent=user.name||user.email||'CrownPath User';
  document.querySelector('#sessionRole').textContent='Role: '+String(user.role||'').replaceAll('_',' ');
  ownerPanel.hidden=user.role!=='OWNER';
  if(user.role==='OWNER'){ownerActivation.hidden=true;loadOwnerUsers()}
}

function clearSession(){sessionCard.hidden=true;ownerPanel.hidden=true;userList.innerHTML=''}

async function checkSession(){
  try{showSession(await jsonRequest('/api/auth/me'))}
  catch(_){clearSession()}
}

async function checkOwnerActivation(){
  try{const data=await jsonRequest('/api/auth/owner-activation/status');ownerActivation.hidden=!data.available}
  catch(_){ownerActivation.hidden=true}
}

function userCard(user){
  const wrap=document.createElement('div');wrap.className='session-card';wrap.style.marginTop='12px';
  const identity=document.createElement('div');
  const name=document.createElement('strong');name.textContent=user.name||'CrownPath User';
  const meta=document.createElement('span');meta.textContent=`${user.email} • ${String(user.role).replaceAll('_',' ')} • ${user.active?'Active':'Disabled'}`;
  identity.append(name,document.createElement('br'),meta);wrap.append(identity);
  if(user.role!=='OWNER'){
    const controls=document.createElement('div');controls.className='actions';
    const select=document.createElement('select');
    [['INSTRUCTOR','Instructor'],['HOME_CARE','Home Care Learner'],['BARBER','Barber Learner'],['COSMETOLOGY_PRO','Cosmetology Learner']].forEach(([value,label])=>{const option=document.createElement('option');option.value=value;option.textContent=label;option.selected=value===user.role;select.append(option)});
    const save=document.createElement('button');save.type='button';save.textContent='Save Role';save.addEventListener('click',()=>updateRole(user.user_id,select.value));
    const toggle=document.createElement('button');toggle.type='button';toggle.textContent=user.active?'Disable Access':'Enable Access';toggle.addEventListener('click',()=>updateActive(user.user_id,!user.active));
    controls.append(select,save,toggle);wrap.append(controls);
  }
  return wrap;
}

async function loadOwnerUsers(){
  ownerPanelMessage.textContent='Loading CrownPath accounts…';
  try{const data=await jsonRequest('/api/owner/users');userList.innerHTML='';data.users.forEach(user=>userList.append(userCard(user)));ownerPanelMessage.textContent=`${data.users.length} account(s) loaded.`}
  catch(e){ownerPanelMessage.textContent=e.message}
}

async function updateRole(userId,role){
  ownerPanelMessage.textContent='Updating role…';
  try{await jsonRequest(`/api/owner/users/${encodeURIComponent(userId)}/role`,{method:'PATCH',body:JSON.stringify({role})});ownerPanelMessage.textContent='Role updated successfully.';await loadOwnerUsers()}
  catch(e){ownerPanelMessage.textContent=e.message}
}

async function updateActive(userId,active){
  ownerPanelMessage.textContent=active?'Enabling account…':'Disabling account…';
  try{await jsonRequest(`/api/owner/users/${encodeURIComponent(userId)}/active`,{method:'PATCH',body:JSON.stringify({active})});ownerPanelMessage.textContent=active?'Account enabled.':'Account disabled.';await loadOwnerUsers()}
  catch(e){ownerPanelMessage.textContent=e.message}
}

document.querySelector('#health').addEventListener('click',showHealth);
document.querySelector('#signInJump').addEventListener('click',()=>document.querySelector('#access').scrollIntoView({behavior:'smooth'}));
document.querySelector('#refreshUsers').addEventListener('click',loadOwnerUsers);

document.querySelectorAll('[data-role]').forEach(b=>b.addEventListener('click',async()=>{
  try{const d=await jsonRequest('/api/avatar/startup/'+b.dataset.role);guide.textContent=d.message}
  catch(_){guide.textContent='Avatar guide is temporarily unavailable.'}
}));

document.querySelector('#ownerActivationForm').addEventListener('submit',async event=>{
  event.preventDefault();ownerMessage.textContent='Activating Owner account…';
  try{const data=await jsonRequest('/api/auth/owner-activation',{method:'POST',body:JSON.stringify({name:document.querySelector('#ownerName').value,email:document.querySelector('#ownerEmail').value,password:document.querySelector('#ownerPassword').value,activation_code:document.querySelector('#ownerCode').value})});ownerMessage.textContent='Owner account activated successfully.';showSession(data.user);event.target.reset();ownerActivation.hidden=true}
  catch(e){ownerMessage.textContent=e.message}
});

document.querySelector('#loginForm').addEventListener('submit',async event=>{
  event.preventDefault();loginMessage.textContent='Signing in…';
  try{const data=await jsonRequest('/api/auth/login',{method:'POST',body:JSON.stringify({email:document.querySelector('#loginEmail').value,password:document.querySelector('#loginPassword').value})});if(data.mfa_required){loginMessage.textContent='Multi-factor authentication is required for this account.';return}loginMessage.textContent='Signed in successfully.';showSession(data.user);event.target.reset()}
  catch(e){loginMessage.textContent=e.message}
});

document.querySelector('#registerForm').addEventListener('submit',async event=>{
  event.preventDefault();registerMessage.textContent='Creating account…';
  try{const data=await jsonRequest('/api/auth/register',{method:'POST',body:JSON.stringify({name:document.querySelector('#registerName').value,email:document.querySelector('#registerEmail').value,password:document.querySelector('#registerPassword').value,role:document.querySelector('#registerRole').value})});registerMessage.textContent='Learner account created and signed in.';showSession(data.user);event.target.reset()}
  catch(e){registerMessage.textContent=e.message}
});

document.querySelector('#logoutButton').addEventListener('click',async()=>{
  try{await jsonRequest('/api/auth/logout',{method:'POST'});clearSession();loginMessage.textContent='Signed out.'}
  catch(e){loginMessage.textContent=e.message}
});

showHealth();checkSession();checkOwnerActivation();
