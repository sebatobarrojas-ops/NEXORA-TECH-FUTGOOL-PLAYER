(() => {
 const toggle=document.getElementById('chat-toggle'), panel=document.getElementById('chat-panel'), close=document.getElementById('chat-close');
 const messages=document.getElementById('chat-messages'), form=document.getElementById('chat-form'), input=document.getElementById('chat-input');
 const questions=[
 ['⚽ ¿Cómo creo un partido?','¿Cómo creo un partido?'],
 ['👥 ¿Cómo me inscribo?','¿Cómo me inscribo en un partido?'],
 ['📊 Mis estadísticas','¿Dónde veo mis estadísticas?'],
 ['🏆 Ranking','¿Cómo funciona el ranking?'],
 ['👤 Crear una cuenta','¿Cómo creo una cuenta?'],
 ['💬 Comunidad','¿Cómo uso la comunidad?']
 ];
 const whatsapp='https://wa.me/56942173052?text='+encodeURIComponent('Hola, vengo de FUTGOOL PLAYER y necesito hablar con un agente de NEXORA TECH.');
 function bubble(t,who='bot'){const el=document.createElement('p');el.className='chat-bubble '+who;el.textContent=t;messages.appendChild(el);messages.scrollTop=messages.scrollHeight;return el;}
 function button(label,handler,kind=''){const b=document.createElement('button');b.type='button';b.className='nexo-choice '+kind;b.textContent=label;b.addEventListener('click',handler);return b;}
 function choices(){const wrap=document.createElement('div');wrap.className='nexo-choices';questions.forEach(([label,q])=>wrap.appendChild(button(label,()=>ask(q))));wrap.appendChild(button('🗓️ Ver horarios y reservar cancha',showDate,'accent'));wrap.appendChild(button('🟢 Hablar con un agente por WhatsApp',()=>window.open(whatsapp,'_blank','noopener,noreferrer'),'whatsapp'));messages.appendChild(wrap);messages.scrollTop=messages.scrollHeight;}
 async function ask(q){bubble(q,'human');const wait=bubble('Consultando…');try{const r=await fetch('/api/chatbot',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:q})});const d=await r.json();wait.textContent=r.ok?d.reply:(d.error||'No se pudo consultar.');}catch(e){wait.textContent='No se pudo conectar al servidor.';}choices();}
 function localDate(){const d=new Date();return [d.getFullYear(),String(d.getMonth()+1).padStart(2,'0'),String(d.getDate()).padStart(2,'0')].join('-');}
 function showDate(){bubble('🗓️ Consultar disponibilidad de las 14 canchas','human');bubble('Cada reserva dura 1 hora. Selecciona la fecha para ver los turnos desde las 13:00 hasta las 22:00.');const wrap=document.createElement('div');wrap.className='nexo-date';const lbl=document.createElement('label');lbl.textContent='Fecha de la reserva';const date=document.createElement('input');date.type='date';date.min=localDate();date.value=localDate();lbl.appendChild(date);wrap.appendChild(lbl);wrap.appendChild(button('Consultar horarios',()=>loadSlots(date.value),'accent'));messages.appendChild(wrap);messages.scrollTop=messages.scrollHeight;}
 async function loadSlots(day){
  const wait=bubble('Consultando horarios del '+day+'…');
  try{
   const r=await fetch('/api/canchas/disponibilidad?fecha='+encodeURIComponent(day));
   const data=await r.json();
   if(!r.ok){wait.textContent=data.error||'Error al consultar';return;}
   wait.textContent='Selecciona un horario. Cada partido dura exactamente una hora:';
   const wrap=document.createElement('div');wrap.className='nexo-slots';
   data.turnos.forEach(slot=>{
    const b=button(`${slot.inicio}–${slot.fin} · ${slot.disponibles}/14 libres`,()=>showCourts(day,slot),slot.disponibles?'':'soldout');
    wrap.appendChild(b);
   });
   messages.appendChild(wrap);messages.scrollTop=messages.scrollHeight;
  }catch(e){wait.textContent='No se pudo consultar la disponibilidad.';}
 }
 function showCourts(day,slot){
  bubble(`Horario ${slot.inicio}–${slot.fin}: elige una cancha del 1 al 14. Las ocupadas muestran quién la reservó.`);
  const wrap=document.createElement('div');wrap.className='nexo-courts';
  slot.canchas.forEach(c=>{
   const label=c.disponible?`Cancha ${c.numero} · Libre`:`Cancha ${c.numero} · Ocupada por ${c.reservado_por}`;
   const b=button(label,()=>reserve(day,slot.hora,c.numero),c.disponible?'':'soldout');
   b.disabled=!c.disponible;wrap.appendChild(b);
  });
  messages.appendChild(wrap);messages.scrollTop=messages.scrollHeight;
 }
 async function reserve(day,hour,court){
  const label=`${String(hour).padStart(2,'0')}:00–${String(hour+1).padStart(2,'0')}:00`;
  if(!window.confirm(`¿Confirmar reserva de cancha ${court} para ${day}, ${label}?`))return;
  bubble(`Reservar cancha ${court} · ${day} · ${label}`,'human');
  const wait=bubble('Verificando disponibilidad…');
  try{
   const r=await fetch('/api/canchas/reservar',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({fecha:day,hora:hour,cancha:court})});
   if(r.redirected){wait.textContent='Debes iniciar sesión para reservar. Ingresa a tu cuenta y vuelve a consultar.';return;}
   const data=await r.json();
   wait.textContent=r.ok?`¡Reserva confirmada! Cancha ${data.cancha}, ${data.fecha}, ${data.inicio}–${data.fin}. Reservada por ${data.reservado_por}.`:(data.error||'No se pudo reservar.');
   if(r.ok||r.status===409)await loadSlots(day);
  }catch(e){wait.textContent='No se pudo registrar la reserva.';}
 }
 function open(state){panel.hidden=!state;toggle.setAttribute('aria-expanded',String(state));}
 toggle.addEventListener('click',()=>open(panel.hidden));close.addEventListener('click',()=>open(false));
 form.addEventListener('submit',e=>{e.preventDefault();const q=input.value.trim();if(!q)return;input.value='';ask(q);});
 choices();
})();