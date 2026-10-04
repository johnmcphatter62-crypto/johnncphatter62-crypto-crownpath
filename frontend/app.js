const output=document.querySelector('#output');
const guide=document.querySelector('#guide');
const loginMessage=document.querySelector('#loginMessage');
const registerMessage=document.querySelector('#registerMessage');
const ownerMessage=document.querySelector('#ownerMessage');
const sessionCard=document.querySelector('#sessionCard');
const ownerActivation=document.querySelector('#ownerActivation');
const ownerPanel=document.querySelector('#ownerPanel');
const learnerDashboard=document.querySelector('#learnerDashboard');
const lessonViewer=document.querySelector('#lessonViewer');
const instructorRequestPanel=document.querySelector('#instructorRequestPanel');
const instructorRequestMessage=document.querySelector('#instructorRequestMessage');
const requestReviewMessage=document.querySelector('#requestReviewMessage');
const requestList=document.querySelector('#requestList');
const ownerPanelMessage=document.querySelector('#ownerPanelMessage');
const userList=document.querySelector('#userList');
const mfaLoginForm=document.querySelector('#mfaLoginForm');
const mfaSetupPanel=document.querySelector('#mfaSetupPanel');
const mfaSetupButton=document.querySelector('#mfaSetupButton');
const mfaSetupMessage=document.querySelector('#mfaSetupMessage');
const mfaRecoveryPanel=document.querySelector('#mfaRecoveryPanel');
const mfaRecoveryCodes=document.querySelector('#mfaRecoveryCodes');
const curriculumMessage=document.querySelector('#curriculumMessage');
const curriculumStructure=document.querySelector('#curriculumStructure');
let activeLessonId=null;
let mfaChallenge=null;
async function jsonRequest(url,options={}){const response=await fetch(url,{...options,headers:{'Content-Type':'application/json',...(options.headers||{})}});let data={};try{data=await response.json()}catch(_){data={}}if(!response.ok)throw new Error(data.detail||'CrownPath request could not be completed.');return data}
async function showHealth(){try{output.textContent=JSON.stringify(await jsonRequest('/api/health'),null,2)}catch(e){output.textContent='CrownPath health check unavailable: '+e.message}}
function resetMfaLogin(){mfaChallenge=null;mfaLoginForm.hidden=true;document.querySelector('#loginForm').hidden=false;document.querySelector('#mfaLoginCode').value=''}
function hideRecoveryCodes(){mfaRecoveryCodes.textContent='';mfaRecoveryPanel.hidden=true}
function showSession(user){resetMfaLogin();sessionCard.hidden=false;document.querySelector('#sessionName').textContent=user.name||user.email||'CrownPath User';document.querySelector('#sessionRole').textContent='Role: '+String(user.role||'').replaceAll('_',' ');mfaSetupButton.hidden=Boolean(user.mfa_enabled);mfaSetupPanel.hidden=true;hideRecoveryCodes();document.querySelector('#mfaSecret').value='';document.querySelector('#mfaEnableCode').value='';mfaSetupMessage.textContent=user.mfa_enabled?'MFA is enabled for this account.':'';const isLearner=!['OWNER','INSTRUCTOR'].includes(user.role);ownerPanel.hidden=user.role!=='OWNER';learnerDashboard.hidden=!isLearner;instructorRequestPanel.hidden=!isLearner;if(user.role==='OWNER'){ownerActivation.hidden=true;loadOwnerUsers();loadInstructorRequests();loadOwnerCurriculum()}else if(isLearner){loadLearnerDashboard();loadMyInstructorRequests()}}
function clearSession(){resetMfaLogin();sessionCard.hidden=true;mfaSetupPanel.hidden=true;hideRecoveryCodes();ownerPanel.hidden=true;learnerDashboard.hidden=true;lessonViewer.hidden=true;activeLessonId=null;instructorRequestPanel.hidden=true;userList.innerHTML='';requestList.innerHTML='';document.querySelector('#learnerModules').innerHTML='';document.querySelector('#learnerDigital').innerHTML=''}
async function checkSession(){try{showSession(await jsonRequest('/api/auth/me'))}catch(_){clearSession()}}
async function checkOwnerActivation(){try{const data=await jsonRequest('/api/auth/owner-activation/status');ownerActivation.hidden=!data.available}catch(_){ownerActivation.hidden=true}}
function academyItem(title,meta){const wrap=document.createElement('div');wrap.className='session-card';wrap.style.marginTop='10px';const strong=document.createElement('strong');strong.textContent=title;const span=document.createElement('span');span.textContent=meta;wrap.append(strong,document.createElement('br'),span);return wrap}
function lessonItem(item){const wrap=academyItem(item.title,`${String(item.status).replaceAll('_',' ')} • ${item.progress||0}% complete`);const controls=document.createElement('div');controls.className='actions';controls.style.marginTop='8px';const open=document.createElement('button');open.type='button';open.textContent=item.status==='NOT_STARTED'?'Open Lesson':item.status==='COMPLETED'?'Review Lesson':'Continue Lesson';open.addEventListener('click',()=>openLesson(item.lesson_id));controls.append(open);wrap.append(controls);return wrap}
function fillList(element,items){element.innerHTML='';(items||[]).forEach(text=>{const li=document.createElement('li');li.textContent=text;element.append(li)})}
function renderLessonSteps(lesson){const list=document.querySelector('#lessonSteps');list.innerHTML='';const steps=lesson.content?.steps||[];const completed=new Set(lesson.completed_steps||[]);steps.forEach((text,index)=>{const stepNumber=index+1;const li=document.createElement('li');li.style.marginBottom='10px';const label=document.createElement('span');label.textContent=text+' ';const button=document.createElement('button');button.type='button';button.textContent=completed.has(stepNumber)?'Step Completed':'Mark Step Complete';button.disabled=completed.has(stepNumber)||lesson.status==='COMPLETED';button.addEventListener('click',()=>completeLessonStep(lesson.lesson_id,stepNumber,button));li.append(label,button);list.append(li)})}
function showLesson(lesson){activeLessonId=lesson.lesson_id;const content=lesson.content||{};document.querySelector('#lessonTitle').textContent=lesson.title;document.querySelector('#lessonSummary').textContent=content.summary||'';fillList(document.querySelector('#lessonObjectives'),content.objectives);renderLessonSteps(lesson);document.querySelector('#lessonSafety').textContent=content.safety_note||'';const complete=document.querySelector('#lessonComplete');complete.disabled=true;complete.textContent=lesson.status==='COMPLETED'?'Lesson Completed':'Complete each step above to finish';lessonViewer.hidden=false;lessonViewer.scrollIntoView({behavior:'smooth',block:'start'})}
async function openLesson(lessonId){const next=document.querySelector('#learnerNextStep');next.textContent='Opening lesson…';try{const data=await jsonRequest(`/api/learner/lessons/${encodeURIComponent(lessonId)}/open`,{method:'POST'});showLesson(data.lesson);await loadLearnerDashboard(false)}catch(e){next.textContent=e.message}}
async function completeLessonStep(lessonId,stepIndex,button){const next=document.querySelector('#learnerNextStep');button.disabled=true;button.textContent='Saving…';try{const data=await jsonRequest(`/api/learner/lessons/${encodeURIComponent(lessonId)}/steps/${stepIndex}/complete`,{method:'POST'});button.textContent='Step Completed';next.textContent=`Lesson progress: ${data.lesson.progress}%`;await loadLearnerDashboard(false);if(data.lesson.status==='COMPLETED'){document.querySelector('#lessonComplete').disabled=true;document.querySelector('#lessonComplete').textContent='Lesson Completed'}}catch(e){button.disabled=false;button.textContent='Mark Step Complete';next.textContent=e.message}}
async function loadLearnerDashboard(closeLesson=true){try{const data=await jsonRequest('/api/learner/dashboard');document.querySelector('#learnerPathwayTitle').textContent=data.pathway+' Pathway';document.querySelector('#learnerNextStep').textContent='Next step: '+(data.next_step||'Continue your CrownPath training.');document.querySelector('#learnerProgress').textContent=`${data.overall_progress||0}%`;const modules=document.querySelector('#learnerModules');const digital=document.querySelector('#learnerDigital');modules.innerHTML='';digital.innerHTML='';data.modules.forEach(item=>modules.append(lessonItem(item)));data.digital_content.forEach(item=>digital.append(academyItem(item.title,String(item.type).replaceAll('_',' '))));if(closeLesson){lessonViewer.hidden=true;activeLessonId=null}}catch(e){document.querySelector('#learnerNextStep').textContent=e.message}}
function userCard(user){const wrap=document.createElement('div');wrap.className='session-card';wrap.style.marginTop='12px';const identity=document.createElement('div');const name=document.createElement('strong');name.textContent=user.name||'CrownPath User';const meta=document.createElement('span');meta.textContent=`${user.email} • ${String(user.role).replaceAll('_',' ')} • ${user.active?'Active':'Disabled'}`;identity.append(name,document.createElement('br'),meta);wrap.append(identity);if(user.role!=='OWNER'){const controls=document.createElement('div');controls.className='actions';const select=document.createElement('select');[['HOME_CARE','Home Care Learner'],['BARBER','Barber Learner'],['COSMETOLOGY_PRO','Cosmetology Learner']].forEach(([value,label])=>{const option=document.createElement('option');option.value=value;option.textContent=label;option.selected=value===user.role;select.append(option)});if(user.role==='INSTRUCTOR'){const option=document.createElement('option');option.value='INSTRUCTOR';option.textContent='Instructor (approved)';option.selected=true;select.append(option)}const save=document.createElement('button');save.type='button';save.textContent='Save Role';save.addEventListener('click',()=>updateRole(user.user_id,select.value));const toggle=document.createElement('button');toggle.type='button';toggle.textContent=user.active?'Disable Access':'Enable Access';toggle.addEventListener('click',()=>updateActive(user.user_id,!user.active));controls.append(select,save,toggle);wrap.append(controls)}return wrap}
function fillCurriculumSelect(id,items,valueKey,labelKey){const select=document.querySelector(id);select.innerHTML='';items.forEach(item=>{const option=document.createElement('option');option.value=item[valueKey];option.textContent=item[labelKey];select.append(option)})}
function curriculumProgramCard(program){const wrap=academyItem(program.title,`${program.slug} • ${String(program.status||'DRAFT').replaceAll('_',' ')}`);if(program.description){const p=document.createElement('p');p.textContent=program.description;wrap.append(p)}return wrap}
async function loadOwnerCurriculum(){
  curriculumMessage.textContent='Loading CrownPath curriculum…';
  try{
    const data=await jsonRequest('/api/owner/curriculum');
    const programs=data.programs||[],courses=data.courses||[],units=data.units||[],lessons=data.lessons||[];
    curriculumStructure.innerHTML='';
    programs.forEach(program=>curriculumStructure.append(curriculumProgramCard(program)));
    courses.forEach(item=>curriculumStructure.append(academyItem('Course: '+item.title,`${item.slug} • sequence ${item.sequence} • ${item.status}`)));
    units.forEach(item=>curriculumStructure.append(academyItem('Unit: '+item.title,`sequence ${item.sequence}`)));
    lessons.forEach(item=>curriculumStructure.append(academyItem('Lesson: '+item.title,`sequence ${item.sequence} • ${item.status}`)));
    fillCurriculumSelect('#curriculumCourseProgram',programs,'program_id','title');
    fillCurriculumSelect('#curriculumUnitCourse',courses,'course_id','title');
    fillCurriculumSelect('#curriculumLessonUnit',units,'unit_id','title');
    fillCurriculumSelect('#curriculumVersionLesson',lessons,'lesson_id','title');
    fillCurriculumSelect('#curriculumReviewLesson',lessons,'lesson_id','title');
    curriculumMessage.textContent=`${programs.length} program(s), ${courses.length} course(s), ${units.length} unit(s), and ${lessons.length} lesson(s) loaded.`;
  }catch(e){curriculumStructure.innerHTML='';curriculumMessage.textContent=e.message.includes('does not exist')?'Curriculum activation is still pending. Your production database has not been changed.':e.message}
}
async function submitCurriculumDraft(event,url,payload,message){event.preventDefault();curriculumMessage.textContent=message;try{await jsonRequest(url,{method:'POST',body:JSON.stringify(payload())});event.target.reset();await loadOwnerCurriculum()}catch(e){curriculumMessage.textContent=e.message}}
async function createCurriculumProgram(event){return submitCurriculumDraft(event,'/api/owner/curriculum/programs',()=>({title:document.querySelector('#curriculumProgramTitle').value,slug:document.querySelector('#curriculumProgramSlug').value,description:document.querySelector('#curriculumProgramDescription').value.trim()||null}),'Creating draft program…')}
async function createCurriculumCourse(event){return submitCurriculumDraft(event,'/api/owner/curriculum/courses',()=>({program_id:document.querySelector('#curriculumCourseProgram').value,title:document.querySelector('#curriculumCourseTitle').value,slug:document.querySelector('#curriculumCourseSlug').value,sequence:Number(document.querySelector('#curriculumCourseSequence').value)}),'Creating draft course…')}
async function createCurriculumUnit(event){return submitCurriculumDraft(event,'/api/owner/curriculum/units',()=>({course_id:document.querySelector('#curriculumUnitCourse').value,title:document.querySelector('#curriculumUnitTitle').value,sequence:Number(document.querySelector('#curriculumUnitSequence').value)}),'Creating draft unit…')}
async function createCurriculumLesson(event){return submitCurriculumDraft(event,'/api/owner/curriculum/lessons',()=>({unit_id:document.querySelector('#curriculumLessonUnit').value,title:document.querySelector('#curriculumLessonTitle').value,sequence:Number(document.querySelector('#curriculumLessonSequence').value)}),'Creating draft lesson…')}
async function createCurriculumVersion(event){event.preventDefault();const raw=document.querySelector('#curriculumVersionContent').value.trim();try{JSON.parse(raw)}catch(_){curriculumMessage.textContent='Lesson content must be valid JSON.';return}return submitCurriculumDraft(event,'/api/owner/curriculum/lesson-versions',()=>({lesson_id:document.querySelector('#curriculumVersionLesson').value,version:Number(document.querySelector('#curriculumVersionNumber').value),content_json:raw}),'Saving unapproved lesson version…')}
function curriculumVersionCard(item){
  const wrap=academyItem(`Version ${item.version}`,item.approved?'Owner approved':'Awaiting Owner approval');
  const content=document.createElement('pre');content.textContent=item.content_json||'';wrap.append(content);
  if(!item.approved){const approve=document.createElement('button');approve.type='button';approve.textContent='Approve This Version';approve.addEventListener('click',()=>approveCurriculumVersion(item.version_id));wrap.append(approve)}
  return wrap
}
async function loadCurriculumVersions(){
  const lessonId=document.querySelector('#curriculumReviewLesson').value, message=document.querySelector('#curriculumReviewMessage'), list=document.querySelector('#curriculumVersionList');
  if(!lessonId){message.textContent='Create or select a lesson first.';return}
  message.textContent='Loading lesson versions…';list.innerHTML='';
  try{const data=await jsonRequest(`/api/owner/curriculum/lessons/${encodeURIComponent(lessonId)}/versions`);(data.versions||[]).forEach(item=>list.append(curriculumVersionCard(item)));message.textContent=(data.versions||[]).length?`${data.versions.length} version(s) ready for Owner review.`:'No versions have been saved for this lesson yet.'}catch(e){message.textContent=e.message}
}
async function approveCurriculumVersion(versionId){
  const message=document.querySelector('#curriculumReviewMessage');message.textContent='Recording Owner approval…';
  try{await jsonRequest('/api/owner/curriculum/lesson-versions/approve',{method:'POST',body:JSON.stringify({version_id:versionId})});message.textContent='Version approved by Owner. It has not been published to learners.';await loadCurriculumVersions()}catch(e){message.textContent=e.message}
}
async function loadReviewQueue(){
  const list=document.querySelector('#reviewQueue');list.innerHTML='';
  try{
    const data=await jsonRequest('/api/owner/curriculum/review-queue');
    list.append(academyItem('Status',String(data.status)),academyItem('Lessons waiting',String(data.queue_count)));
    (data.queue||[]).slice(0,25).forEach(item=>list.append(academyItem(item.title,String(item.review_state)+' · saved versions '+String(item.saved_versions))));
  }catch(e){curriculumMessage.textContent=e.message}
}
async function loadCurriculumCompletion(){
  const list=document.querySelector('#curriculumCompletion');list.innerHTML='';
  try{
    const data=await jsonRequest('/api/owner/curriculum/completion-dashboard');
    [['Status',data.status],['Completion',String(data.completion_percent)+'%'],['Programs',data.programs],['Courses',data.courses],['Units',data.units],['Lessons',data.lessons],['Lessons completed',data.lessons_completed],['Lessons remaining',data.lessons_remaining],['Approved versions',data.approved_versions]].forEach(([label,value])=>list.append(academyItem(label,String(value))));
  }catch(e){curriculumMessage.textContent=e.message}
}
async function loadCurriculumAudit(){
  const list=document.querySelector('#curriculumAudit');list.innerHTML='';
  try{
    const data=await jsonRequest('/api/owner/curriculum/structure-audit');
    [['Status',data.status],['Blockers',data.blocker_count],['Orphaned courses',data.orphaned_courses.length],['Orphaned units',data.orphaned_units.length],['Orphaned lessons',data.orphaned_lessons.length],['Orphaned versions',data.orphaned_versions.length],['Lessons missing approval',data.lessons_without_approved_version.length]].forEach(([label,value])=>list.append(academyItem(label,String(value))));
  }catch(e){curriculumMessage.textContent=e.message}
}
async function loadCurriculumProgress(){
  const list=document.querySelector('#curriculumProgress');list.innerHTML='';
  try{
    const data=await jsonRequest('/api/owner/curriculum/progress-summary');
    [['Programs',data.programs],['Courses',data.courses],['Units',data.units],['Lessons',data.lessons],['Saved versions',data.saved_versions],['Approved versions',data.approved_versions],['Lessons waiting for approval',data.lessons_waiting_for_approval]].forEach(([label,value])=>list.append(academyItem(label,String(value))));
  }catch(e){curriculumMessage.textContent=e.message}
}
async function loadMigrationReadiness(){
  const list=document.querySelector('#migrationReadiness');list.innerHTML='';
  try{
    const data=await jsonRequest('/api/owner/curriculum/migration-readiness');
    list.append(academyItem('Overall migration status',data.overall_status||'BLOCKED'));
    list.append(academyItem('Database integrity',data.integrity?.verification_status||'UNVERIFIED'));
    list.append(academyItem('Recovery evidence packet',data.recovery_packet?.status||'INCOMPLETE'));
    list.append(academyItem('Owner verification decision',data.verification_gate?.status||'LOCKED'));
    list.append(academyItem('Migration authorization',data.migration_gate?.status||'LOCKED'));
    list.append(academyItem('Curriculum readiness',data.curriculum?.ready_for_activation_review?'Ready for Owner review':'Not ready for Owner review'));
    (data.migration_gate?.blockers||[]).forEach(item=>list.append(academyItem('Blocker',item)));
  }catch(e){curriculumMessage.textContent=e.message}
}
async function loadCurriculumActivationPlan(){
  const list=document.querySelector('#curriculumActivationPlan');list.innerHTML='';
  try{
    const data=await jsonRequest('/api/owner/curriculum/activation-plan');
    (data.steps||[]).forEach(item=>list.append(academyItem(`${item.sequence}. ${item.label}`,item.performed?'Performed':'Not performed')));
    (data.blockers||[]).forEach(item=>list.append(academyItem('Blocker',item)));
  }catch(e){curriculumMessage.textContent=e.message}
}
async function loadCurriculumReadiness(){
  const list=document.querySelector('#curriculumReadiness');list.innerHTML='';
  try{
    const data=await jsonRequest('/api/owner/curriculum/readiness');
    (data.checks||[]).forEach(item=>list.append(academyItem(item.label,item.ready?`Ready • ${item.count}`:`Missing • ${item.count}`)));
    list.append(academyItem(data.ready_for_activation_review?'Ready for Owner activation review':'Not ready for activation review','This check does not activate curriculum or open learner access.'));
  }catch(e){curriculumMessage.textContent=e.message}
}
async function loadCurriculumApprovalHistory(){
  const list=document.querySelector('#curriculumApprovalHistory');list.innerHTML='';
  try{const data=await jsonRequest('/api/owner/curriculum/approval-history');(data.approvals||[]).forEach(item=>list.append(academyItem(item.reason||'Curriculum approval',`${item.result} • ${item.created_at||''}`)))}catch(e){curriculumMessage.textContent=e.message}
}
async function loadOwnerUsers(){ownerPanelMessage.textContent='Loading CrownPath accounts…';try{const data=await jsonRequest('/api/owner/users');userList.innerHTML='';data.users.forEach(user=>userList.append(userCard(user)));ownerPanelMessage.textContent=`${data.users.length} account(s) loaded.`}catch(e){ownerPanelMessage.textContent=e.message}}
async function updateRole(userId,role){ownerPanelMessage.textContent='Updating role…';try{await jsonRequest(`/api/owner/users/${encodeURIComponent(userId)}/role`,{method:'PATCH',body:JSON.stringify({role})});await loadOwnerUsers()}catch(e){ownerPanelMessage.textContent=e.message}}
async function updateActive(userId,active){ownerPanelMessage.textContent=active?'Enabling account…':'Disabling account…';try{await jsonRequest(`/api/owner/users/${encodeURIComponent(userId)}/active`,{method:'PATCH',body:JSON.stringify({active})});await loadOwnerUsers()}catch(e){ownerPanelMessage.textContent=e.message}}
function requestCard(item){const wrap=document.createElement('div');wrap.className='session-card';wrap.style.marginTop='12px';const info=document.createElement('div');const title=document.createElement('strong');title.textContent=item.applicant?.name||'CrownPath Applicant';const meta=document.createElement('span');meta.textContent=`${item.applicant?.email||''} • ${item.status}`;const statement=document.createElement('p');statement.textContent=item.statement||'';info.append(title,document.createElement('br'),meta,statement);if(item.review_note){const prior=document.createElement('p');prior.textContent='Owner review note: '+item.review_note;info.append(prior)}wrap.append(info);if(item.status==='PENDING'){const noteLabel=document.createElement('label');noteLabel.textContent='Owner review note (optional)';const note=document.createElement('textarea');note.maxLength=1000;note.rows=3;note.placeholder='Record qualifications checked, reason for decision, or follow-up needed.';noteLabel.append(note);wrap.append(noteLabel);const controls=document.createElement('div');controls.className='actions';const approve=document.createElement('button');approve.type='button';approve.textContent='Approve Instructor';approve.addEventListener('click',()=>reviewInstructorRequest(item.request_id,'APPROVE',note.value));const deny=document.createElement('button');deny.type='button';deny.textContent='Deny';deny.addEventListener('click',()=>reviewInstructorRequest(item.request_id,'DENY',note.value));controls.append(approve,deny);wrap.append(controls)}return wrap}
async function loadInstructorRequests(){requestReviewMessage.textContent='Loading Instructor requests…';try{const data=await jsonRequest('/api/owner/instructor-requests');requestList.innerHTML='';data.requests.forEach(item=>requestList.append(requestCard(item)));requestReviewMessage.textContent=data.requests.length?`${data.requests.length} request(s) loaded.`:'No Instructor requests yet.'}catch(e){requestReviewMessage.textContent=e.message}}
async function reviewInstructorRequest(requestId,decision,note=''){requestReviewMessage.textContent=decision==='APPROVE'?'Approving Instructor…':'Denying request…';try{await jsonRequest(`/api/owner/instructor-requests/${encodeURIComponent(requestId)}`,{method:'PATCH',body:JSON.stringify({decision,note:note.trim()||null})});await loadInstructorRequests();await loadOwnerUsers()}catch(e){requestReviewMessage.textContent=e.message}}
async function loadMyInstructorRequests(){try{const data=await jsonRequest('/api/instructor-requests/me');const pending=data.requests.find(item=>item.status==='PENDING');instructorRequestMessage.textContent=pending?'Your Instructor request is pending Owner review.':''}catch(_){}}
async function startMfaSetup(){hideRecoveryCodes();mfaSetupMessage.textContent='Creating secure authenticator setup…';try{const data=await jsonRequest('/api/auth/mfa/setup',{method:'POST'});document.querySelector('#mfaSecret').value=data.secret||'';mfaSetupPanel.hidden=false;mfaSetupMessage.textContent='Add the setup key to your authenticator app, then enter its current 6-digit code below.'}catch(e){mfaSetupMessage.textContent=e.message;mfaSetupPanel.hidden=false}}
async function enableMfa(){const code=document.querySelector('#mfaEnableCode').value.trim();mfaSetupMessage.textContent='Verifying authenticator code…';try{const data=await jsonRequest('/api/auth/mfa/enable',{method:'POST',body:JSON.stringify({code})});document.querySelector('#mfaSecret').value='';document.querySelector('#mfaEnableCode').value='';mfaSetupButton.hidden=true;const codes=Array.isArray(data.recovery_codes)?data.recovery_codes:[];mfaRecoveryCodes.textContent=codes.join('\n');mfaRecoveryPanel.hidden=!codes.length;mfaSetupPanel.hidden=false;mfaSetupMessage.textContent='MFA is enabled. Save the recovery codes below now; CrownPath will not show this same set again.'}catch(e){mfaSetupMessage.textContent=e.message}}
document.querySelector('#health').addEventListener('click',showHealth);document.querySelector('#signInJump').addEventListener('click',()=>document.querySelector('#access').scrollIntoView({behavior:'smooth'}));document.querySelector('#refreshUsers').addEventListener('click',loadOwnerUsers);document.querySelector('#refreshCurriculum').addEventListener('click',loadOwnerCurriculum);document.querySelector('#curriculumProgramForm').addEventListener('submit',createCurriculumProgram);document.querySelector('#curriculumCourseForm').addEventListener('submit',createCurriculumCourse);document.querySelector('#curriculumUnitForm').addEventListener('submit',createCurriculumUnit);document.querySelector('#curriculumLessonForm').addEventListener('submit',createCurriculumLesson);document.querySelector('#curriculumVersionForm').addEventListener('submit',createCurriculumVersion);document.querySelector('#loadCurriculumVersions').addEventListener('click',loadCurriculumVersions);document.querySelector('#loadCurriculumApprovalHistory').addEventListener('click',loadCurriculumApprovalHistory);document.querySelector('#loadCurriculumReadiness').addEventListener('click',loadCurriculumReadiness);document.querySelector('#loadCurriculumActivationPlan').addEventListener('click',loadCurriculumActivationPlan);document.querySelector('#loadMigrationReadiness').addEventListener('click',loadMigrationReadiness);document.querySelector('#loadCurriculumProgress').addEventListener('click',loadCurriculumProgress);document.querySelector('#loadCurriculumAudit').addEventListener('click',loadCurriculumAudit);document.querySelector('#loadCurriculumCompletion').addEventListener('click',loadCurriculumCompletion);document.querySelector('#loadReviewQueue').addEventListener('click',loadReviewQueue);document.querySelector('#refreshRequests').addEventListener('click',loadInstructorRequests);document.querySelector('#lessonClose').addEventListener('click',()=>{lessonViewer.hidden=true;activeLessonId=null});document.querySelector('#mfaSetupButton').addEventListener('click',startMfaSetup);document.querySelector('#mfaEnableButton').addEventListener('click',enableMfa);document.querySelector('#mfaCancelSetup').addEventListener('click',()=>{mfaSetupPanel.hidden=true;hideRecoveryCodes();document.querySelector('#mfaSecret').value='';document.querySelector('#mfaEnableCode').value='';mfaSetupMessage.textContent=''});document.querySelector('#cancelMfaLogin').addEventListener('click',()=>{resetMfaLogin();loginMessage.textContent='MFA verification cancelled.'});document.querySelectorAll('[data-role]').forEach(b=>b.addEventListener('click',async()=>{try{const d=await jsonRequest('/api/avatar/startup/'+b.dataset.role);guide.textContent=d.message}catch(_){guide.textContent='Avatar guide is temporarily unavailable.'}}));
document.querySelector('#instructorRequestForm').addEventListener('submit',async event=>{event.preventDefault();instructorRequestMessage.textContent='Submitting Instructor request…';try{await jsonRequest('/api/instructor-requests',{method:'POST',body:JSON.stringify({statement:document.querySelector('#instructorStatement').value})});instructorRequestMessage.textContent='Instructor request submitted for Owner review.';event.target.reset()}catch(e){instructorRequestMessage.textContent=e.message}});
document.querySelector('#ownerActivationForm').addEventListener('submit',async event=>{event.preventDefault();ownerMessage.textContent='Activating Owner account…';try{const data=await jsonRequest('/api/auth/owner-activation',{method:'POST',body:JSON.stringify({name:document.querySelector('#ownerName').value,email:document.querySelector('#ownerEmail').value,password:document.querySelector('#ownerPassword').value,activation_code:document.querySelector('#ownerCode').value})});ownerMessage.textContent='Owner account activated successfully.';showSession(data.user);event.target.reset();ownerActivation.hidden=true}catch(e){ownerMessage.textContent=e.message}});
document.querySelector('#loginForm').addEventListener('submit',async event=>{event.preventDefault();loginMessage.textContent='Signing in…';try{const data=await jsonRequest('/api/auth/login',{method:'POST',body:JSON.stringify({email:document.querySelector('#loginEmail').value,password:document.querySelector('#loginPassword').value})});if(data.mfa_required){mfaChallenge=data.challenge;document.querySelector('#loginPassword').value='';event.target.hidden=true;mfaLoginForm.hidden=false;loginMessage.textContent='Enter a 6-digit authenticator code or an unused 8-digit recovery code.';document.querySelector('#mfaLoginCode').focus();return}loginMessage.textContent='Signed in successfully.';showSession(data.user);event.target.reset()}catch(e){loginMessage.textContent=e.message}});
document.querySelector('#mfaLoginForm').addEventListener('submit',async event=>{event.preventDefault();loginMessage.textContent='Verifying security code…';try{const data=await jsonRequest('/api/auth/mfa/verify',{method:'POST',body:JSON.stringify({challenge:mfaChallenge,code:document.querySelector('#mfaLoginCode').value.trim()})});loginMessage.textContent='Signed in successfully with MFA.';showSession(data.user);document.querySelector('#loginForm').reset()}catch(e){loginMessage.textContent=e.message}});
document.querySelector('#registerForm').addEventListener('submit',async event=>{event.preventDefault();registerMessage.textContent='Creating account…';try{const data=await jsonRequest('/api/auth/register',{method:'POST',body:JSON.stringify({name:document.querySelector('#registerName').value,email:document.querySelector('#registerEmail').value,password:document.querySelector('#registerPassword').value,role:document.querySelector('#registerRole').value})});registerMessage.textContent='Learner account created and signed in.';showSession(data.user);event.target.reset()}catch(e){registerMessage.textContent=e.message}});
document.querySelector('#logoutButton').addEventListener('click',async()=>{try{await jsonRequest('/api/auth/logout',{method:'POST'});clearSession();loginMessage.textContent='Signed out.'}catch(e){loginMessage.textContent=e.message}});showHealth();checkSession();checkOwnerActivation();