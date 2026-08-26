const output=document.querySelector('#output');
const guide=document.querySelector('#guide');
const loginMessage=document.querySelector('#loginMessage');
const registerMessage=document.querySelector('#registerMessage');
const ownerMessage=document.querySelector('#ownerMessage');
const sessionCard=document.querySelector('#sessionCard');
const ownerActivation=document.querySelector('#ownerActivation');

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
  if(user.role==='OWNER') ownerActivation.hidden=true;
}

function clearSession(){sessionCard.hidden=true}

async function checkSession(){
  try{showSession(await jsonRequest('/api/auth/me'))}
  catch(_){clearSession()}
}

async function checkOwnerActivation(){
  try{const data=await jsonRequest('/api/auth/owner-activation/status');ownerActivation.hidden=!data.available}
  catch(_){ownerActivation.hidden=true}
}

document.querySelector('#health').addEventListener('click',showHealth);
document.querySelector('#signInJump').addEventListener('click',()=>document.querySelector('#access').scrollIntoView({behavior:'smooth'}));

document.querySelectorAll('[data-role]').forEach(b=>b.addEventListener('click',async()=>{
  try{const d=await jsonRequest('/api/avatar/startup/'+b.dataset.role);guide.textContent=d.message}
  catch(_){guide.textContent='Avatar guide is temporarily unavailable.'}
}));

document.querySelector('#ownerActivationForm').addEventListener('submit',async event=>{
  event.preventDefault();ownerMessage.textContent='Activating Owner account…';
  try{
    const data=await jsonRequest('/api/auth/owner-activation',{method:'POST',body:JSON.stringify({name:document.querySelector('#ownerName').value,email:document.querySelector('#ownerEmail').value,password:document.querySelector('#ownerPassword').value,activation_code:document.querySelector('#ownerCode').value})});
    ownerMessage.textContent='Owner account activated successfully.';showSession(data.user);event.target.reset();ownerActivation.hidden=true;
  }catch(e){ownerMessage.textContent=e.message}
});

document.querySelector('#loginForm').addEventListener('submit',async event=>{
  event.preventDefault();loginMessage.textContent='Signing in…';
  try{
    const data=await jsonRequest('/api/auth/login',{method:'POST',body:JSON.stringify({email:document.querySelector('#loginEmail').value,password:document.querySelector('#loginPassword').value})});
    if(data.mfa_required){loginMessage.textContent='Multi-factor authentication is required for this account.';return}
    loginMessage.textContent='Signed in successfully.';showSession(data.user);event.target.reset();
  }catch(e){loginMessage.textContent=e.message}
});

document.querySelector('#registerForm').addEventListener('submit',async event=>{
  event.preventDefault();registerMessage.textContent='Creating account…';
  try{
    const data=await jsonRequest('/api/auth/register',{method:'POST',body:JSON.stringify({name:document.querySelector('#registerName').value,email:document.querySelector('#registerEmail').value,password:document.querySelector('#registerPassword').value,role:document.querySelector('#registerRole').value})});
    registerMessage.textContent='Learner account created and signed in.';showSession(data.user);event.target.reset();
  }catch(e){registerMessage.textContent=e.message}
});

document.querySelector('#logoutButton').addEventListener('click',async()=>{
  try{await jsonRequest('/api/auth/logout',{method:'POST'});clearSession();loginMessage.textContent='Signed out.'}
  catch(e){loginMessage.textContent=e.message}
});

showHealth();checkSession();checkOwnerActivation();
