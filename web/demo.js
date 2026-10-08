let session, busy = false, guided = false, view = 'customer';
const $ = id => document.getElementById(id);
const activeStatuses = ['NEEDS_CUSTOMER_DETAILS','AWAITING_OWNER','PAYMENT_PENDING','PAID','READY'];
const statusLabels = {DISCOVERY:'Listening to the customer',NEEDS_CUSTOMER_DETAILS:'Waiting for customer details',AWAITING_OWNER:'Ready for owner review',PAYMENT_PENDING:'Owner confirmed · awaiting acceptance',PAID:'Demo paid · preparing request',READY:'Ready for collection / shipment',COMPLETED:'Request completed',DECLINED:'Owner declined request',CANCELLED:'Customer cancelled request'};
const time = at => new Date(at).toLocaleTimeString('en-US',{hour:'numeric',minute:'2-digit',timeZone:'America/New_York'});
function node(tag, cls, text) { const e = document.createElement(tag); if(cls)e.className=cls; if(text!==undefined)e.textContent=text; return e; }
function error(message) { $('error').textContent=message||''; $('error').hidden=!message; }
async function api(path, body) {
  const r = await fetch(path,{method:body===undefined?'GET':'POST',headers:{'Content-Type':'application/json'},...(body===undefined?{}:{body:JSON.stringify(body)})});
  if(!r.ok){ let d;try{d=await r.json()}catch{};throw Error(typeof d?.detail==='string'?d.detail:'Unable to save this step. Please try again.'); }
  return r.json();
}
async function update(path, body) { session=await api(path,body); localStorage.setItem('julians-session',session.id); render();return session; }
function base(){return '/api/sessions/'+session.id;}
function setBusy(value){busy=value;document.querySelectorAll('button').forEach(b=>b.disabled=value);if(!value&&session)renderProductLocks();}
async function act(fn) { if(busy)return;setBusy(true);error();try{await fn()}catch(e){error(e.message)}finally{setBusy(false)} }
async function send(role,message) { await update(base()+'/messages',{role,message}); }
function renderChat(lane){
  const target=$(lane+'-chat'), previous=target.dataset.last;
  const messages=session.messages.filter(m=>m.lane===lane);
  target.replaceChildren();
  messages.forEach(m=>{const row=node('div','message'+(m.sender===lane?' from-person':''));const label=node('div','message-label');label.append(node('span','',m.sender===lane?(lane==='customer'?'Customer · you':'Owner · you'):'Concierge'),node('time','',time(m.at)));row.append(label,node('div','bubble',m.text));target.append(row)});
  const last=messages.at(-1)?.id;
  if(previous!==last){target.scrollTop=target.scrollHeight;target.dataset.last=last;}
}
function renderProductLocks(){document.querySelectorAll('[data-select]').forEach(b=>b.disabled=busy||activeStatuses.includes(session.status));}
function render(){
  renderChat('customer');renderChat('owner');
  $('status').textContent=statusLabels[session.status]||session.status;
  $('request-id').textContent=(session.ticket?'Ticket '+session.ticket.id.slice(0,8):'Conversation '+session.id.slice(0,8))+' · '+session.kind;
  $('mobile-count').textContent=session.status==='AWAITING_OWNER'?'•':'';
  const stages=['Collect details','Owner review','Customer acceptance','Preparation','Ready','Completed'];
  const index={DISCOVERY:0,NEEDS_CUSTOMER_DETAILS:0,AWAITING_OWNER:1,PAYMENT_PENDING:2,PAID:3,READY:4,COMPLETED:5}[session.status];
  $('steps').replaceChildren(...stages.map((label,i)=>node('li',index===i?'current':index>i?'done':'',label)));
  $('preferences').replaceChildren();
  const brief=session.kind==='alteration'&&session.ticket?{
    garments:session.ticket.extraction.items.map(i=>i.garment).join(', ')||'Missing',
    changes:session.ticket.extraction.items.map(i=>i.alteration_types.join(', ')).join('; ')||'Missing',
    deadline:session.ticket.extraction.deadline_text||'Not specified',
    contact:session.ticket.extraction.contact.email||session.ticket.extraction.contact.phone||'Missing',
    missing:(session.missing_details||[]).join(', ')||'None',
    question:session.owner_question||'None'
  }:session.preferences;
  if(!Object.keys(brief).length)$('preferences').append(node('dt','','Waiting for a request'));
  Object.entries(brief).forEach(([k,v])=>{$('preferences').append(node('dt','',k.replaceAll('_',' ')),node('dd','',k==='budget'?'$'+v:v))});
  $('selection-title').textContent=session.kind==='alteration'?'Owner’s intake ticket':'Owner handoff';
  const chosen=session.selected;
  if(chosen){$('selection').textContent=chosen.product.title+' · '+chosen.variant.title+' · $'+chosen.variant.price;}
  else if(session.ticket){
    const original=session.initial_request||session.ticket.raw_message.split('\nCustomer follow-up:')[0];
    $('selection').replaceChildren(node('p','', 'Original request: '+original),node('p','', 'Ticket '+session.ticket.id.slice(0,8)+' · '+(session.ticket.handoff_reasons.map(r=>r.replaceAll('_',' ').toLowerCase()).join(' · ')||'Shop confirmation required')));
  }
  else $('selection').textContent='Describe an alteration or select a product to create a review request.';
  $('owner-task').textContent=session.status==='NEEDS_CUSTOMER_DETAILS'?'Agent is collecting: '+(session.owner_question||(session.missing_details||[]).join(', ')):session.status==='AWAITING_OWNER'?'Your review is needed. Ask for more details, quote an alteration, approve an item, or decline.':session.status==='PAID'?'Payment simulated. Prepare the request, then text “ready …”.':session.status==='READY'?'Ready notification sent. Text “complete …” after collection.':'No decision pending · '+(statusLabels[session.status]||session.status);
  $('checkout').hidden=session.status!=='PAYMENT_PENDING';
  if(session.quote){$('quote-amount').textContent='$'+session.quote.amount;$('quote-details').textContent=session.quote.details;}
  $('events').replaceChildren(...session.events.slice().reverse().map(e=>{const li=node('li');li.append(node('time','',time(e.at)),node('span','',e.text));return li}));
  $('structured').textContent=JSON.stringify({status:session.status,preferences:session.preferences,ticket:session.ticket,missing_details:session.missing_details,owner_question:session.owner_question,selected:session.selected,quote:session.quote,payment:session.payment},null,2);
  renderProducts();setView(view);
}
function renderProducts(){
  const products=session.recommendations;
  if(!products.length){$('products').replaceChildren();const empty=node('div','empty-catalog');empty.append(node('span','empty-mark','✧'),node('h3','',session.kind==='alteration'?'The owner’s ticket is the source of truth.':'Good taste starts with listening.'),node('p','',session.kind==='alteration'?'The agent collects missing details, updates the ticket, and returns it to the owner.':'Describe a budget, category, size and color to find matching catalog variants.'));$('products').append(empty);$('match-count').textContent=session.kind==='alteration'?'Alteration workflow active.':Object.keys(session.preferences).length?'No match in the partial catalog.':'Start a conversation to find your fit.';return;}
  // Keep dropdown choices across owner/customer updates.
  const choices=new Map([...document.querySelectorAll('[data-variant]')].map(e=>[e.dataset.variant,e.value]));
  $('products').replaceChildren();$('match-count').textContent=products.length+' matches · availability snapshot Oct 8, 2026';
  products.forEach(p=>{
    const card=node('article','product'),media=node('div','product-image');
    if(p.image){const img=node('img');img.src=p.image;img.alt=p.title;img.loading='lazy';img.referrerPolicy='no-referrer';img.onerror=()=>{media.replaceChildren(node('span','muted','Product image unavailable'));};media.append(img);}
    const body=node('div','product-body');body.append(node('div','product-brand',p.brand),node('h3','',p.title));
    const price=node('div');price.append(node('span','price','From $'+p.price));const link=node('a','product-link','View at Julian’s ↗');link.href=p.url;link.target='_blank';link.rel='noopener';price.append(link);body.append(price);
    const reasons=node('ul');p.reasons.forEach(r=>reasons.append(node('li','',r)));body.append(reasons);
    const id='variant-'+p.id,label=node('label','','Available variant in snapshot');label.htmlFor=id;
    const select=node('select');select.id=id;select.dataset.variant=p.id;p.variants.forEach(v=>{const opt=node('option','',v.title+' · $'+v.price);opt.value=v.id;select.append(opt)});if(choices.has(p.id)&&p.variants.some(v=>v.id===choices.get(p.id)))select.value=choices.get(p.id);
    const button=node('button','primary','Ask owner to confirm →');button.dataset.select=p.id;button.onclick=()=>act(async()=>{await update(base()+'/select',{product_id:p.id,variant_id:select.value});if(matchMedia('(max-width:680px)').matches){setView('owner');scrollTo({top:0,behavior:'smooth'})}});
    body.append(label,select,button);card.append(media,body);$('products').append(card);
  });renderProductLocks();
}
function setView(next){view=next;document.querySelectorAll('.mobile-tabs button').forEach(b=>b.classList.toggle('active',b.dataset.view===next));document.querySelectorAll('[data-pane]').forEach(e=>e.classList.toggle('mobile-hidden',e.dataset.pane!==next));}
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>setView(b.dataset.view));
for(const role of ['customer','owner']){
  $(role+'-form').onsubmit=e=>{e.preventDefault();const input=$(role+'-input');const text=input.value.trim();if(text)act(async()=>{await send(role,text);input.value=''});};
  $(role+'-input').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();$(role+'-form').requestSubmit();}});
}
document.querySelectorAll('[data-customer]').forEach(b=>b.onclick=()=>act(()=>send('customer',b.dataset.customer)));
document.querySelectorAll('[data-owner]').forEach(b=>b.onclick=()=>{$('owner-input').value=b.dataset.owner;$('owner-input').focus()});
$('pay').onclick=()=>act(()=>update(base()+'/pay',{}));
$('reset').onclick=()=>act(async()=>{await update('/api/sessions',{});setView('customer');$('customer-input').value='';$('owner-input').value=''});
$('export').onclick=()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(session,null,2)],{type:'application/json'}));const a=node('a');a.href=url;a.download='julians-demo-'+session.id.slice(0,8)+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)};
const pause=()=>new Promise(r=>setTimeout(r,1100));
$('guided').onclick=()=>act(async()=>{
  guided=true;const label=$('guided').textContent;try{
    await update('/api/sessions',{});setView('customer');$('guided').textContent='1 / 7 · Customer requests pants hemming';
    await send('customer','I need my pants hemmed by Friday for a wedding.');await pause();
    $('guided').textContent='2 / 7 · Agent collects missing contact';await send('customer','My name is Alex Demo. My email is demo@example.com.');await pause();
    $('guided').textContent='3 / 7 · Owner asks a question';setView('owner');await send('owner','ask customer what material are the pants?');await pause();
    $('guided').textContent='4 / 7 · Answer returns to owner';setView('customer');await send('customer','They are silk. I already own them.');await pause();
    $('guided').textContent='5 / 7 · Owner provides a quote';setView('owner');await send('owner','quote $45 ready by Friday at 3pm; bring the garment for fitting');await pause();
    $('guided').textContent='6 / 7 · Customer accepts';setView('operations');await update(base()+'/pay',{});await pause();
    $('guided').textContent='7 / 7 · Owner fulfills request';await send('owner','ready — your demo alteration is ready for pickup');await pause();await send('owner','complete — customer collected their garment');
  }finally{guided=false;$('guided').textContent=label;}
});
(async()=>{setBusy(true);try{const sid=localStorage.getItem('julians-session');if(sid){try{session=await api('/api/sessions/'+encodeURIComponent(sid));render()}catch(e){if(!e.message.includes('Conversation not found'))throw e;}}if(!session)await update('/api/sessions',{});}catch(e){error(e.message+' Check that the local server is running.')}finally{setBusy(false)}})();
