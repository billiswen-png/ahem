const $ = s => document.querySelector(s);
const roles = {manager:'管理版',operator:'企業版',viewer:'會議閱覽',observer:'受限觀察者',support:'SaaS 服務後台'};
const labels = {analytics:'會議分析',meetings:'內容與授權',health:'服務狀態',audit:'存取稽核'};
const descriptions = {
 analytics:'比較會議時長與主席介入，這裡不載入姓名或逐字稿。',
 meetings:'逐場授權。受限會議須由管理員配置內容許可。',
 health:'只呈現服務代碼與最近回報狀態，不包含客戶會議內容。',
 audit:'追蹤存取與授權結果；紀錄不含逐字稿。'
};
let identity, current = 'analytics', revision = 0;
const el = (tag, text, cls) => {
 const node = document.createElement(tag);
 if (text !== undefined) node.textContent = text;
 if (cls) node.className = cls;
 return node;
};
function error(e) { $('#status').className = 'error'; $('#status').textContent = e.message; }
function signedOut() {
 revision++;
 identity = null;
 $('#workspace').hidden = true; $('#login').hidden = false; $('#logout').hidden = true;
 $('#panel').replaceChildren(); $('#token').value = '';
 document.body.classList.remove('authenticated'); $('#sidebar').hidden = true; $('#context').hidden = true;
}
async function api(path, body, method) {
 const response = await fetch('/api/' + path, {
  method: method || (body ? 'POST' : 'GET'),
  headers: body ? {'Content-Type':'application/json'} : {},
  body: body ? JSON.stringify(body) : undefined
 });
 const data = await response.json();
 if (!response.ok) {
  if (response.status === 401) signedOut();
  const messages = {401:'憑證無效或工作階段已到期，請重新登入。',403:'此角色沒有存取權限。',404:'會議不存在、已到期，或不在您的授權範圍內。',429:'嘗試次數過多，請稍後再試。',400:'資料格式不正確，請檢查輸入內容。'};
  throw Error(messages[response.status] || '服務暫時無法完成操作，請稍後再試。');
 }
 return data;
}
function button(text, action, cls) {
 const b = el('button', text, cls); b.type = 'button';
 b.onclick = async () => {
  if (b.disabled) return;
  const epoch = revision; b.disabled = true; b.setAttribute('aria-busy','true');
  try { await action(); } catch(e) { if (epoch === revision || !identity) error(e); }
  finally { b.disabled = false; b.removeAttribute('aria-busy'); }
 };
 return b;
}
function field(text, control) {
 const box = el('div', undefined, 'field'), label = el('label', text);
 control.id = 'field-' + text; label.htmlFor = control.id; control.setAttribute('aria-label',text);
 box.append(label, control); return box;
}
function select(options) {
 const node = el('select');
 for (const [value, label] of options) { const o = el('option',label); o.value = value; node.append(o); }
 return node;
}
function table(headers, rows) {
 const wrap = el('div',undefined,'table-wrap'), t = el('table'), head = el('tr'), thead = el('thead'), body = el('tbody');
 headers.forEach(x => { const h = el('th',x); h.scope = 'col'; head.append(h); });
 thead.append(head);
 rows.forEach(row => { const tr = el('tr'); row.forEach(x => { const td = el('td'); td.append(x instanceof Node ? x : el('span',String(x))); tr.append(td); }); body.append(tr); });
 t.append(thead,body); wrap.append(t); return wrap;
}
async function start() {
 identity = await api('me');
 $('#login').hidden = true; $('#workspace').hidden = false; $('#logout').hidden = false;
 document.body.classList.add('authenticated'); $('#sidebar').hidden = false; $('#context').hidden = false;
 $('#context').textContent = identity.tenant + ' / ' + (identity.regulated_content ? '受限內容管理' : roles[identity.role]);
 $('#role-art').className = identity.regulated_content ? 'cleared' : identity.role;
 const tabs = identity.role === 'operator' ? ['analytics','meetings','health','audit'] : identity.role === 'support' ? ['health'] : identity.role === 'viewer' ? ['meetings'] : ['analytics'];
 current = tabs[0];
 $('#nav').replaceChildren(...tabs.map(t => {
  const b = button(labels[t],async () => { current=t; await render(); });
  b.prepend(navIcon(t)); return b;
 }));
 await render();
}
$('#login-form').onsubmit = async e => {
 e.preventDefault();
 const b = e.currentTarget.querySelector('button'); if (b.disabled) return;
 const token = $('#token').value; $('#token').value = ''; $('#status').textContent = '';
 b.disabled = true; b.textContent = '登入中…';
 try { await api('login',{token}); await start(); } catch(e) { error(e); }
 finally { b.disabled = false; b.textContent = '進入工作台'; }
};
$('#logout').onclick = async () => {
 $('#logout').disabled = true;
 try { await api('logout',{}); signedOut(); $('#status').textContent=''; $('#token').focus(); }
 catch(e) { error(e); } finally { $('#logout').disabled = false; }
};
$('#refresh').onclick = () => render().catch(error);

async function render() {
 if (!identity) return;
 const epoch = ++revision, page = current, pane = $('#panel');
 pane.replaceChildren(el('p','正在載入…','loading')); pane.setAttribute('aria-busy','true');
 $('#refresh').disabled = true; $('#status').textContent = '';
 $('#title').textContent = labels[page]; $('#description').textContent = descriptions[page];
 [...$('#nav').children].forEach(b => { const active=b.textContent===labels[page]; b.classList.toggle('active',active); if(active)b.setAttribute('aria-current','page'); else b.removeAttribute('aria-current'); });
 try {
  const data = await api(page === 'meetings' ? 'analytics' : page);
  if (epoch !== revision || !identity) return;
  const fragment = document.createDocumentFragment();
  if (page === 'health') renderHealth(fragment,data);
  else if (page === 'audit') renderAudit(fragment,data);
  else renderMeetings(fragment,data,page);
  pane.replaceChildren(fragment);
 } catch(e) {
  if (epoch === revision) { pane.replaceChildren(el('p','無法載入資料，請使用重新整理再試。','empty')); error(e); }
 } finally {
  if (epoch === revision || !identity) { pane.setAttribute('aria-busy','false'); $('#refresh').disabled=false; }
 }
}
function renderHealth(pane,data) {
 const names = {chair:'主席判斷',discord:'Discord 連線',stt:'即時轉錄',tts:'主席語音'};
 const states = {unknown:'尚無有效回報',ok:'正常',degraded:'效能下降',unavailable:'無法使用'};
 for (const c of data.components) {
  const row=el('div',undefined,'row'), title=el('div');
  title.append(el('h2',names[c.component]),el('p',c.updated_at ? '最後回報：'+new Date(c.updated_at*1000).toLocaleString() : '等待服務監測回報','small'));
  row.append(title,el('strong',states[c.state],'state '+c.state)); pane.append(row);
 }
}
function renderAudit(pane,data) {
 const actions={login:'登入',import:'匯入會議',grant:'授予閱覽',revoke:'撤銷閱覽',delete:'刪除會議',access:'權限檢查',content:'內容讀取','content:meeting_review':'讀取：會議回顧','content:incident_review':'讀取：事件調查'};
 if (!data.entries.length) { pane.append(el('p','目前尚無存取紀錄。','empty')); return; }
 pane.append(table(['時間','操作身分指紋','動作','結果'],data.entries.map(x => [new Date(x.at*1000).toLocaleString(),x.actor,actions[x.action]||x.action,x.outcome==='ok'?'成功':'拒絕'])));
}
function importForm() {
 const form=el('form',undefined,'import'), file=el('input'); file.type='file'; file.accept='.jsonl'; file.required=true;
 const policy=select([['team','一般團隊'],['regulated','受限內容']]), days=el('input');
 days.type='number'; days.min=1; days.max=30; days.step=1; days.value=7; days.required=true;
 const submit=el('button','匯入事件檔'); submit.type='submit';
 form.append(field('Ahem 事件檔',file),field('會議政策',policy),field('保存天數',days),submit);
 form.onsubmit=async e => {
  e.preventDefault(); if(submit.disabled)return;
  submit.disabled=true; submit.textContent='匯入中…'; const epoch=revision;
  try {
   const source=file.files[0];
   if (!source || source.size>4000000) throw Error('請選擇不超過 4 MB 的 JSONL 事件檔。');
   let events;
   try { events=(await source.text()).trim().split('\n').filter(x=>x.trim()).map(JSON.parse); }
   catch { throw Error('JSONL 格式不正確，請確認每一行都是完整的 JSON 事件。'); }
   if (!events.length || events.length>10000) throw Error('事件數必須介於 1 至 10,000 筆。');
   if(epoch!==revision)return;
   await api('meetings',{events,policy:policy.value,days:Number(days.value)});
   if(epoch===revision){ await render(); $('#status').className='success'; $('#status').textContent='會議已匯入，統計已更新。'; }
  } catch(e) { if(epoch===revision)error(e); }
  finally { submit.disabled=false; submit.textContent='匯入事件檔'; }
 };
 return form;
}
function renderMeetings(pane,data,page) {
 const stats=el('div',undefined,'stats');
 for(const [v,l] of [[data.count,'場會議'],[data.total_minutes,'累計分鐘'],[data.meetings.reduce((s,m)=>s+m.interventions,0),'主席介入']]) {
  const n=el('div',undefined,'stat'); n.append(el('strong',v),el('span',l)); stats.append(n);
 }
 pane.append(stats);
 if(page==='meetings' && identity.role==='operator')pane.append(importForm());
 if(!data.meetings.length){pane.append(el('p','目前沒有可查看的會議。請先匯入事件或取得會議授權。','empty'));return;}
 pane.append(table(['會議代碼','政策','分鐘','參與人數','發言段數','主席介入',...(page==='meetings'?['操作']:[])],data.meetings.map(m=>{
  const row=[m.id.slice(0,8),m.policy==='regulated'?'受限內容':'團隊',(m.duration_seconds/60).toFixed(1),m.participants,m.utterances,m.interventions];
  if(page==='meetings'){
   const actions=el('div',undefined,'actions');
   if(m.policy!=='regulated' || identity.regulated_content) {
    actions.append(button('查看內容',()=>detail(m)));
    if(identity.role==='operator')actions.append(button('管理授權',()=>grants(m),'secondary'));
   } else actions.append(el('span','需受限內容許可','small'));
   if(identity.role==='operator')actions.append(button('刪除',async()=>{
    if(confirm('永久刪除此場會議的儲存內容與授權？')){
     await api('meetings/'+m.id,null,'DELETE'); await render();
    }
   },'danger'));
   row.push(actions);
  }
  return row;
 })));
}
function detailPane(title) {
 document.querySelector('.detail')?.remove();
 const pane=el('section',undefined,'detail'), heading=el('div',undefined,'detail-heading'), h=el('h2',title);
 h.tabIndex=-1;
 heading.append(h,button('關閉',()=>pane.remove(),'secondary')); pane.append(heading);
 $('#panel').append(pane); h.focus({preventScroll:true}); pane.scrollIntoView({block:'nearest'});
 return pane;
}
function detail(m) {
 const pane=detailPane('內容存取用途'), purpose=select([['meeting_review','會議回顧'],['incident_review','事件調查']]);
 pane.append(field('內容存取用途',purpose),button('確認讀取',async()=>{
  const epoch=revision;
  const data=await api('meetings/'+m.id+'/content',{purpose:purpose.value});
  if(epoch!==revision || !identity || !pane.isConnected)return;
  const list=el('div',undefined,'transcript');
  pane.replaceChildren(el('h2','會議內容'),button('關閉',()=>pane.remove(),'secondary'));
  for(const e of data.events){
   if(e.kind==='meeting')pane.append(el('h3',e.data.topic||'會議'));
   if(e.kind==='utterance'||e.kind==='spoken')list.append(el('p',(e.data.speaker||'主席')+'：'+(e.data.text||''),e.kind==='spoken'?'chair':undefined));
  }
  pane.append(list);
  if(!list.children.length)pane.append(el('p','這份事件檔沒有逐字稿。'));
 }));
}
async function grants(m) {
 const epoch=revision, data=await api('meetings/'+m.id+'/grants');
 if(epoch!==revision || !identity)return;
 const pane=detailPane('會議閱覽授權');
 if(!data.viewers.length)pane.append(el('p','此組織尚未配置閱覽帳號。'));
 for(const a of data.viewers){
  const row=el('div',undefined,'row');
  row.append(el('span',a.id),button(a.granted?'撤銷閱覽':'允許閱覽',async()=>{
   await api('meetings/'+m.id+'/grants',{actor:a.id,allow:!a.granted});
   if(epoch===revision && pane.isConnected)await grants(m);
  },a.granted?'danger':undefined));pane.append(row);
 }
}
function navIcon(kind) {
 const paths = {
  analytics:['M5 20V12','M12 20V4','M19 20V8'],
  meetings:['M6 10V7a6 6 0 0 1 12 0v3','M5 10h14v11H5z','M12 14v3'],
  health:['M2 12h4l3-8 5 16 3-8h5'],
  audit:['M8 3H5v18h14V3h-3','M9 2h6v4H9z','M8 10h8','M8 14h8','M8 18h5']
 };
 const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
 for(const [k,v] of Object.entries({viewBox:'0 0 24 24',fill:'none',stroke:'currentColor','stroke-width':'1.7','stroke-linecap':'round','stroke-linejoin':'round','aria-hidden':'true',focusable:'false'}))svg.setAttribute(k,v);
 for(const d of paths[kind]){const path=document.createElementNS(svg.namespaceURI,'path');path.setAttribute('d',d);svg.append(path);}
 return svg;
}
start().catch(e => { if(identity)error(e); });
