const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const api = async (url, options={}) => {
  const response = await fetch(url,{headers:{"Content-Type":"application/json"},...options});
  const data = await response.json().catch(()=>({error:"The server returned an unreadable response."}));
  if(!response.ok || data.ok===false) throw new Error(data.error || "Something went wrong.");
  return data;
};
const toast = (message) => { const el=$("#toast"); el.textContent=message; el.classList.add("show"); clearTimeout(toast.timer); toast.timer=setTimeout(()=>el.classList.remove("show"),2600); };
const esc = (s="") => String(s).replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const dateLabel = (s) => { if(!s)return ""; const d=new Date(s+"T00:00:00"); return isNaN(d)?s:d.toLocaleDateString(undefined,{day:"numeric",month:"short"}); };

// Friendly section navigation
const navLinks=$$(".nav-link");
const pageNames={home:"Overview",assistant:"AI Assistant",planner:"Academic Rescue",finder:"Classroom Finder",skills:"Skill Exchange",lost:"Lost & Found",green:"Green Campus"};
function updateNav(){const id=location.hash.slice(1)||"home";navLinks.forEach(a=>a.classList.toggle("active",a.getAttribute("href")==="#"+id));$("#currentPage").textContent=pageNames[id]||"Overview";}
window.addEventListener("hashchange",updateNav);updateNav();
$("#themeButton").addEventListener("click",()=>document.body.classList.toggle("dark"));

// Assistant: local intelligent demo logic, not a hosted LLM.
function addChat(text,who,source=""){const row=document.createElement("div");row.className="chat-row "+(who==="user"?"user":"");const bubble=document.createElement("div");bubble.className=who==="user"?"user-bubble":"bot-bubble";bubble.textContent=text;row.appendChild(bubble);if(source&&who!=="user"){const wrap=document.createElement("div");wrap.appendChild(row);const label=document.createElement("div");label.className="source-label";label.textContent="Source: "+source;wrap.appendChild(label);$("#chatMessages").appendChild(wrap);}else $("#chatMessages").appendChild(row);$("#chatMessages").scrollTop=$("#chatMessages").scrollHeight;}
async function sendChat(text){const q=text.trim();if(!q)return;addChat(q,"user");$("#chatInput").value="";$("#chatInput").disabled=true;try{const d=await api("/api/chat",{method:"POST",body:JSON.stringify({message:q})});addChat(d.reply,"bot",d.source);}catch(e){addChat("I couldn't reach the CampusMate server. Check that the app is running, then try again.","bot");}finally{$("#chatInput").disabled=false;$("#chatInput").focus();}}
$("#chatForm").addEventListener("submit",e=>{e.preventDefault();sendChat($("#chatInput").value);});
$$(".prompt-chip").forEach(b=>b.addEventListener("click",()=>sendChat(b.dataset.prompt)));
$("#clearChat").addEventListener("click",()=>{$("#chatMessages").replaceChildren();addChat("Fresh start! What can I help you with? ✨","bot");});
$("#voiceButton").addEventListener("click",()=>{const Speech=window.SpeechRecognition||window.webkitSpeechRecognition;if(!Speech){toast("Voice input isn't supported in this browser. Try Chrome.");return;}const recognition=new Speech();recognition.lang="en-IN";recognition.interimResults=false;recognition.onresult=e=>{$("#chatInput").value=e.results[0][0].transcript;sendChat($("#chatInput").value);};recognition.onerror=()=>toast("Microphone unavailable. Check browser permissions.");recognition.start();});

// Academic Rescue
let tasks=[];
async function loadTasks(){const d=await api("/api/tasks");tasks=d.tasks;renderTasks();}
function renderTasks(){const list=$("#taskList");list.replaceChildren();tasks.forEach(t=>{const li=document.createElement("li");li.className="task-item"+(t.done?" done":"");const cb=document.createElement("input");cb.type="checkbox";cb.checked=!!t.done;cb.setAttribute("aria-label","Mark task complete");cb.addEventListener("change",async()=>{try{await api(`/api/tasks/${t.id}`,{method:"PATCH",body:JSON.stringify({done:cb.checked})});await loadTasks();}catch(e){toast(e.message);}});const span=document.createElement("span");span.textContent=t.title;const meta=document.createElement("small");meta.textContent=[t.subject,dateLabel(t.due_date)].filter(Boolean).join(" · ");span.appendChild(meta);const del=document.createElement("button");del.className="delete-btn";del.textContent="×";del.setAttribute("aria-label","Delete task");del.addEventListener("click",async()=>{try{await api(`/api/tasks/${t.id}`,{method:"DELETE"});await loadTasks();}catch(e){toast(e.message);}});li.append(cb,span,del);list.appendChild(li);});const done=tasks.filter(t=>t.done).length,pct=tasks.length?Math.round(done/tasks.length*100):0;$("#taskCount").textContent=`${tasks.length} tasks · ${done} completed`;$(`#progressText`).textContent=pct+"%";$("#progressBar").style.width=pct+"%";$("#taskEmpty").hidden=tasks.length>0;}
$("#taskForm").addEventListener("submit",async e=>{e.preventDefault();try{await api("/api/tasks",{method:"POST",body:JSON.stringify({title:$("#taskTitle").value,subject:$("#taskSubject").value,due_date:$("#taskDate").value})});e.target.reset();await loadTasks();toast("Added to your study plan ✨");}catch(err){toast(err.message);}});

// Classroom Finder
let directory=[];
function renderDirectory(){const q=$("#directorySearch").value.toLowerCase();const found=directory.filter(x=>(x.name+" "+x.category+" "+x.building).toLowerCase().includes(q));$("#directoryGrid").innerHTML=found.map((x,i)=>`<article class="directory-card"><div class="dir-icon">${["▤","⌘","▣","☕","✚"][i%5]}</div><h4>${esc(x.name)}</h4><p>${esc(x.building)}<br>${esc(x.detail)}</p><small>DEMO · VERIFY LOCATION</small></article>`).join("")||'<p class="empty-state">No matching place. Try another search.</p>';}
$("#directorySearch").addEventListener("input",renderDirectory);
async function loadDirectory(){const d=await api("/api/directory");directory=d.items;renderDirectory();}

// Skill Exchange
async function loadSkills(){const d=await api("/api/skills");$("#skillList").innerHTML=d.skills.map(s=>`<div><span><b>${esc(s.name)} <span class="tag">${esc(s.format||"Flexible")}</span></b><small>Can teach: ${esc(s.teaches)} · Wants: ${esc(s.wants||"Not specified")} · ${esc(s.availability||"Availability not set")}</small></span></div>`).join("")||'<p class="empty-state">No skill listings yet. Add the first one!</p>';}
$("#skillForm").addEventListener("submit",async e=>{e.preventDefault();const f=new FormData(e.target);const d=Object.fromEntries(f.entries());d.consent=f.has("consent");try{const result=await api("/api/skills",{method:"POST",body:JSON.stringify(d)});$("#skillFeedback").textContent=result.matches.length?`Possible peer matches: ${result.matches.map(x=>x.name+" — "+x.teaches).join("; ")}`:"Your listing is live in this demo. No direct match yet.";e.target.reset();await loadSkills();toast("Skill added to the circle!");}catch(err){toast(err.message);}});

// Lost & Found
async function loadLost(){const d=await api("/api/lost-found");$("#lostList").innerHTML=d.items.map(x=>`<div><span><b>${esc(x.item)}</b><small>${esc(x.kind.toUpperCase())} · ${esc(x.colour)} · ${esc(x.place)}</small></span><span class="tag">${esc(x.category||"Item")}</span></div>`).join("")||'<p class="empty-state">No reports yet.</p>';}
$("#lostForm").addEventListener("submit",async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target).entries());try{const result=await api("/api/lost-found",{method:"POST",body:JSON.stringify(d)});$("#lostFeedback").textContent=result.matches.length?"Possible matches (please verify):\n"+result.matches.map(x=>`${x.item} · ${x.colour||"colour not listed"} · ${x.place||"place not listed"} · ${x.score}% similarity`).join("\n"):result.note||"Report added. No possible matches found yet.";e.target.reset();await loadLost();toast("Report added.");}catch(err){toast(err.message);}});
// Green Campus
async function loadIssues(){const d=await api("/api/issues");$("#issueList").innerHTML=d.issues.map(x=>`<div><span><b>${esc(x.title)}</b><small>${esc(x.category)} · ${esc(x.place)} · #${x.id}</small></span><select class="status-select status-${x.status.toLowerCase().replace(" ","-")}" data-id="${x.id}" aria-label="Update status"><option ${x.status==="Submitted"?"selected":""}>Submitted</option><option ${x.status==="In progress"?"selected":""}>In progress</option><option ${x.status==="Resolved"?"selected":""}>Resolved</option></select></div>`).join("")||'<p class="empty-state">No maintenance reports yet. Your first report can help.</p>';}
$("#issueForm").addEventListener("submit",async e=>{e.preventDefault();const d=Object.fromEntries(new FormData(e.target).entries());try{const result=await api("/api/issues",{method:"POST",body:JSON.stringify(d)});$("#issueFeedback").textContent=result.duplicate?result.message:`Issue submitted as case #${result.issue.id}.`;e.target.reset();await loadIssues();toast(result.duplicate?"Similar report found.":"Issue submitted.");}catch(err){toast(err.message);}});
$("#issueList").addEventListener("change",async e=>{if(!e.target.matches(".status-select"))return;try{await api(`/api/issues/${e.target.dataset.id}`,{method:"PATCH",body:JSON.stringify({status:e.target.value})});await loadIssues();toast("Demo status updated.");}catch(err){toast(err.message);}});

// Load all sections; show a clear message if the server isn't running.
Promise.all([loadTasks(),loadDirectory(),loadSkills(),loadLost(),loadIssues()]).catch(e=>{toast("Could not load data. Start the Flask server and refresh.");console.error(e);});

// Signed-in student profile and logout
(async()=>{try{const d=await api('/api/me');const user=d.user;const first=user.name.trim().split(/\s+/)[0];$('#welcomeName').textContent=first;$('#profileName').textContent=user.name;$('#profileEmail').textContent=user.email;$('#profileInitial').textContent=user.name.trim().charAt(0).toUpperCase();$('#topInitial').textContent=user.name.trim().charAt(0).toUpperCase();}catch(e){if(e.message.includes('log in'))location.href='/auth';}})();
$('#logoutButton').addEventListener('click',async()=>{try{await api('/api/logout',{method:'POST'});location.href='/auth';}catch(e){toast(e.message);}});
