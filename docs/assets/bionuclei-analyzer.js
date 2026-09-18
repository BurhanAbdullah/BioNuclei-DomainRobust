(() => {
  const cfg = window.BIONUCLEI_CONFIG || {};
  const api = (cfg.apiBase || '').replace(/\/$/, '');
  const authReady = Boolean(cfg.supabaseUrl && cfg.supabasePublishableKey);
  let supa = null;
  let currentToken = '';
  let guestToken = '';
  let currentJob = '';
  let pollTimer = null;
  let previewUrls = [];
  let measurementRows = [];
  let activeMetric = 'area';
  let roi = null;
  let draggingROI = false;
  let roiStart = null;

  const $ = id => document.getElementById(id);
  const message = (id, text, kind = 'error') => {
    const node = $(id);
    if (node) node.innerHTML = `<div class="note">${escapeHtml(text)}</div>`;
  };
  const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const headers = () => guestToken && !currentToken ? {'X-BioNuclei-Guest-Token': guestToken} : (currentToken ? {'Authorization': `Bearer ${currentToken}`} : {});
  const activeAuth = () => Boolean(currentToken || guestToken);

  function setAccessMode(mode) {
    document.querySelectorAll('[data-access-tab]').forEach(tab => {
      const on = tab.dataset.accessTab === mode;
      tab.classList.toggle('is-active', on);
      tab.setAttribute('aria-selected', String(on));
      const panel = document.querySelector(`[data-access-panel="${tab.dataset.accessTab}"]`);
      if (panel) panel.hidden = !on;
    });
  }
  document.querySelectorAll('[data-access-tab]').forEach(tab => tab.addEventListener('click', () => setAccessMode(tab.dataset.accessTab)));

  function showWorkspace(identity) {
    $('access').hidden = true;
    $('workspace').hidden = false;
    $('signout').hidden = !identity.account;
    $('workspace').scrollIntoView({block: 'start', behavior: 'smooth'});
  }
  function showAccess() {
    $('access').hidden = false;
    $('workspace').hidden = true;
    $('resultPanel').hidden = true;
    $('signout').hidden = true;
  }

  async function ensureGuest() {
    if (guestToken) return true;
    if (!api) return message('guestMsg', 'Analyzer endpoint is not configured. Reload the page after the production configuration is available.');
    try {
      const r = await fetch(`${api}/guest-session`, {method:'POST'});
      const j = await r.json();
      if (!r.ok || !j.guest_token) throw Error(j.detail || 'Could not start guest session');
      guestToken = j.guest_token;
      return true;
    } catch (e) { message('guestMsg', e.message); return false; }
  }

  async function signUp() {
    if (!supa) return message('signupMsg', 'Account service is not configured. Guest analysis remains available.');
    const email = $('signupEmail').value.trim();
    const password = $('signupPassword').value;
    if (!email || password.length < 8) return message('signupMsg', 'Enter an email and a password of at least 8 characters.');
    const {data, error} = await supa.auth.signUp({email, password, options:{emailRedirectTo: location.href}});
    if (error) return message('signupMsg', error.message);
    if (data.session) {
      currentToken = data.session.access_token; guestToken = ''; showWorkspace({account:true});
    } else message('signupMsg', 'Account created. Confirm your email if required, then use Sign in.', 'success');
  }
  async function signIn() {
    if (!supa) return message('loginMsg', 'Account service is not configured. Guest analysis remains available.');
    const email = $('loginEmail').value.trim();
    const password = $('loginPassword').value;
    if (!email || !password) return message('loginMsg', 'Enter your email and password.');
    const {data, error} = await supa.auth.signInWithPassword({email, password});
    if (error) return message('loginMsg', error.message);
    currentToken = data.session?.access_token || ''; guestToken = ''; showWorkspace({account:true});
  }
  async function resetPassword() {
    if (!supa) return message('loginMsg', 'Account service is not configured.');
    const email = $('loginEmail').value.trim();
    if (!email) return message('loginMsg', 'Enter your email first.');
    const {error} = await supa.auth.resetPasswordForEmail(email, {redirectTo: location.href});
    if (error) return message('loginMsg', error.message);
    message('loginMsg', 'If password reset is available for this account, Supabase will send the reset message.', 'success');
  }
  async function signOut() {
    if (supa) await supa.auth.signOut();
    currentToken = ''; guestToken = ''; currentJob = ''; clearLocalFile(); clearResult(); showAccess(); setAccessMode('signin');
  }

  function clearLocalFile() {
    const input = $('image');
    if (input) input.value = '';
    $('fileInfo').hidden = true;
    $('nd2Controls').hidden = true;
  }
  function clearResult() {
    clearInterval(pollTimer); pollTimer = null;
    previewUrls.forEach(URL.revokeObjectURL); previewUrls = [];
    measurementRows = []; roi = null;
    $('resultPanel').hidden = true;
    ['overlayPreview','maskPreview'].forEach(id => $(id)?.removeAttribute('src'));
    const canvas = $('analysisCanvas'); if (canvas) canvas.width = canvas.height = 0;
    const table = $('measurementBody'); if (table) table.innerHTML = '';
    const summary = $('roiSummary'); if (summary) summary.textContent = 'Draw a rectangle on the viewer to inspect a spatial subset.';
  }
  function setFile(file) {
    if (!file) return clearLocalFile();
    $('fileInfo').hidden = false;
    $('fileInfo').textContent = `${file.name} · ${(file.size/1048576).toFixed(2)} MiB · held in browser memory only`;
    $('nd2Controls').hidden = !file.name.toLowerCase().endsWith('.nd2');
  }
  function selectedModules() { return ['nuclei','morphology','intensity']; }

  async function runAnalysis() {
    const file = $('image').files[0];
    if (!file) return message('runMsg', 'Choose a TIFF or ND2 image first.');
    if (!api) return message('runMsg', 'Analyzer endpoint is not configured. Reload the page after the production configuration is available.');
    if (!activeAuth()) { message('runMsg', 'Choose Sign up, Sign in, or Guest first.'); $('access').scrollIntoView({behavior:'smooth'}); return; }
    const fd = new FormData();
    fd.append('image', file);
    fd.append('research_consent', 'false');
    fd.append('algorithm_profile', 'auto');
    fd.append('analysis_modules', selectedModules().join(','));
    fd.append('nd2_channel', $('nd2Channel').value);
    fd.append('nd2_time', $('nd2Time').value);
    fd.append('nd2_z', $('nd2Z').value);
    fd.append('nd2_field', $('nd2Field').value);
    $('analyzeButton').disabled = true;
    message('runMsg', 'Sending image for transient analysis…', 'success');
    try {
      const r = await fetch(`${api}/analyze`, {method:'POST', headers:headers(), body:fd});
      const j = await r.json();
      if (!r.ok) throw Error(j.detail || 'Analysis request failed');
      currentJob = j.job_id;
      clearLocalFile();
      poll(j.job_id);
    } catch (e) { $('analyzeButton').disabled = false; message('runMsg', e.message); }
  }
  function poll(id) {
    clearInterval(pollTimer);
    pollTimer = setInterval(async () => {
      try {
        const r = await fetch(`${api}/jobs/${id}`, {headers:headers(), cache:'no-store'});
        const j = await r.json();
        if (!r.ok) throw Error(j.detail || 'Status request failed');
        message('runMsg', `Analysis status: ${j.status}`, 'success');
        if (j.status === 'completed') { clearInterval(pollTimer); $('analyzeButton').disabled = false; await showResult(j); }
        if (j.status === 'failed') { clearInterval(pollTimer); $('analyzeButton').disabled = false; message('runMsg', j.error || 'Analysis failed'); }
      } catch (e) { clearInterval(pollTimer); $('analyzeButton').disabled = false; message('runMsg', e.message); }
    }, 2000);
  }
  async function fetchBlob(path) {
    const r = await fetch(api + path, {headers:headers(), cache:'no-store'});
    if (!r.ok) throw Error(`Could not retrieve ${path.split('/').pop()}`);
    return r.blob();
  }
  async function fetchText(path) {
    const r = await fetch(api + path, {headers:headers(), cache:'no-store'});
    if (!r.ok) throw Error(`Could not retrieve ${path.split('/').pop()}`);
    return r.text();
  }

  function parseCSV(text) {
    const lines = text.trim().split(/\r?\n/);
    if (!lines.length) return [];
    const parseLine = line => { const out=[]; let cur='', quote=false; for(let i=0;i<line.length;i++){const c=line[i]; if(c==='"' && line[i+1]==='"'){cur+='"';i++;continue;} if(c==='"'){quote=!quote;continue;} if(c===','&&!quote){out.push(cur);cur='';} else cur+=c;} out.push(cur); return out; };
    const head=parseLine(lines[0]);
    return lines.slice(1).map(line=>{const vals=parseLine(line), row={}; head.forEach((h,i)=>row[h]=vals[i]??''); return row;}).filter(r=>Object.keys(r).length>0);
  }
  const num = (row, key) => { const n=Number(row[key]); return Number.isFinite(n)?n:null; };
  function normalizedMeasurements(rows) {
    return rows.map((r,i)=>({
      id: num(r,'label') ?? i+1,
      x: num(r,'centroid-1'), y: num(r,'centroid-0'),
      area:num(r,'area'), perimeter:num(r,'perimeter'), eccentricity:num(r,'eccentricity'), solidity:num(r,'solidity'), circularity:num(r,'circularity'),
      mean_intensity:num(r,'mean_intensity'), max_intensity:num(r,'max_intensity'), min_intensity:num(r,'min_intensity')
    }));
  }
  function metricValue(r) {
    return activeMetric === 'intensity' ? r.mean_intensity : activeMetric === 'circularity' ? r.circularity : activeMetric === 'eccentricity' ? r.eccentricity : r.area;
  }
  function renderMeasurementTable() {
    const body=$('measurementBody'); if(!body)return;
    const rows=measurementRows.slice(0,500);
    body.innerHTML=rows.map(r=>`<tr><td>${escapeHtml(r.id)}</td><td>${fmt(r.area)}</td><td>${fmt(r.circularity)}</td><td>${fmt(r.eccentricity)}</td><td>${fmt(r.mean_intensity)}</td><td>${fmt(r.x)}, ${fmt(r.y)}</td></tr>`).join('');
    $('measurementCount').textContent = `${measurementRows.length.toLocaleString()} nuclei · first ${Math.min(500,measurementRows.length).toLocaleString()} shown`;
  }
  function fmt(v){return v==null?'—':Number(v).toFixed(2);}

  function drawCanvas() {
    const canvas=$('analysisCanvas'), img=$('overlayPreview');
    if(!canvas || !img || !img.naturalWidth)return;
    canvas.width=img.naturalWidth; canvas.height=img.naturalHeight;
    canvas.style.aspectRatio=`${canvas.width}/${canvas.height}`;
    const ctx=canvas.getContext('2d'); ctx.clearRect(0,0,canvas.width,canvas.height);
    if(activeMetric){
      const vals=measurementRows.map(metricValue).filter(v=>v!=null); const min=Math.min(...vals), max=Math.max(...vals), span=max-min||1;
      measurementRows.forEach(r=>{if(r.x==null||r.y==null)return; const v=metricValue(r); if(v==null)return; const t=(v-min)/span; ctx.beginPath(); ctx.arc(r.x,r.y,Math.max(2,Math.min(8,2+Math.sqrt(Math.max(r.area||1,1))/12)),0,Math.PI*2); ctx.fillStyle=`hsl(${220-210*t} 80% 50% / 0.65)`;ctx.fill();});
    }
    if(roi){ctx.strokeStyle='white';ctx.lineWidth=Math.max(2,canvas.width/500);ctx.setLineDash([8,6]);ctx.strokeRect(roi.x,roi.y,roi.w,roi.h);ctx.setLineDash([]);}
  }
  function setupROI() {
    const canvas=$('analysisCanvas'); if(!canvas)return;
    canvas.addEventListener('pointerdown',e=>{const r=canvas.getBoundingClientRect();roiStart={x:(e.clientX-r.left)*canvas.width/r.width,y:(e.clientY-r.top)*canvas.height/r.height};draggingROI=true;canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener('pointermove',e=>{if(!draggingROI)return;const r=canvas.getBoundingClientRect(),x=(e.clientX-r.left)*canvas.width/r.width,y=(e.clientY-r.top)*canvas.height/r.height;roi={x:Math.min(roiStart.x,x),y:Math.min(roiStart.y,y),w:Math.abs(x-roiStart.x),h:Math.abs(y-roiStart.y)};drawCanvas();});
    canvas.addEventListener('pointerup',()=>{if(!draggingROI)return;draggingROI=false;updateROI();});
  }
  function updateROI(){
    if(!roi)return;
    const inside=measurementRows.filter(r=>r.x!=null&&r.y!=null&&r.x>=roi.x&&r.x<=roi.x+roi.w&&r.y>=roi.y&&r.y<=roi.y+roi.h);
    const meanArea=inside.length?inside.reduce((s,r)=>s+(r.area||0),0)/inside.length:null;
    const meanIntensity=inside.length?inside.reduce((s,r)=>s+(r.mean_intensity||0),0)/inside.length:null;
    $('roiSummary').textContent=`ROI: ${inside.length.toLocaleString()} nuclei · mean area ${fmt(meanArea)} px² · mean intensity ${fmt(meanIntensity)}`;
  }
  function setMetric(metric){activeMetric=metric;document.querySelectorAll('[data-heatmap]').forEach(b=>b.classList.toggle('is-active',b.dataset.heatmap===metric));drawCanvas();}

  async function showResult(j) {
    const r=j.result||{}, rep=r.reports||{};
    $('resultPanel').hidden=false;
    $('nucleusCount').textContent=rep.nuclei_count??r.n_instances??'Not available';
    $('resultShape').textContent=r.image_shape?r.image_shape.join(' × '):(r.input_metadata?.selected_plane_shape?.join(' × ')||'2-D plane');
    $('reportCount').textContent=(r.analysis_modules||[]).length;
    $('agentDetails').innerHTML='';
    const agents=r.expert_agents?.findings||r.expert_agents?.agents||[];
    if(Array.isArray(agents)) agents.slice(0,8).forEach(a=>{const d=document.createElement('div');d.textContent=(a.agent||a.name||'Specialist')+': '+(a.statement||a.finding||a.summary||'Evidence reviewed');$('agentDetails').appendChild(d);});
    try {
      previewUrls.forEach(URL.revokeObjectURL); previewUrls=[];
      const [overlay,mask,csv] = await Promise.all([fetchBlob(`/jobs/${j.job_id}/preview/overlay.tif`),fetchBlob(`/jobs/${j.job_id}/preview/segmentation_mask.tif`),fetchText(`/jobs/${j.job_id}/files/nuclei_analysis.csv`)]);
      const ou=URL.createObjectURL(overlay),mu=URL.createObjectURL(mask);previewUrls=[ou,mu];
      $('overlayPreview').src=ou;$('maskPreview').src=mu;
      measurementRows=normalizedMeasurements(parseCSV(csv));renderMeasurementTable();
      $('analysisCanvas').style.display='block';
      $('overlayPreview').onload=()=>drawCanvas();
      $('measurementTools').hidden=false;
    } catch(e) { message('resultMsg', `Analysis completed, but an interactive evidence layer could not be loaded: ${e.message}. The report download remains available.`); }
    $('resultPanel').scrollIntoView({behavior:'smooth'});
  }
  async function deleteJob(){
    if(!currentJob||!activeAuth())return;
    try{const r=await fetch(`${api}/jobs/${currentJob}`,{method:'DELETE',headers:headers()});if(!r.ok)throw Error('Delete request failed');currentJob='';clearResult();clearLocalFile();message('resultMsg','All server-side analysis data for this job has been deleted.','success');}
    catch(e){message('resultMsg',e.message);}
  }
  async function downloadReport(){
    if(!currentJob)return message('resultMsg','No completed analysis is available.');
    $('downloadButton').disabled=true;
    try{const blob=await fetchBlob(`/jobs/${currentJob}/download`),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=`bionuclei-${currentJob}.zip`;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);await deleteJob();message('resultMsg','Report received by your browser. The server-side analysis job was then deleted.','success');}
    catch(e){message('resultMsg',e.message);$('downloadButton').disabled=false;}
  }

  $('signupButton').addEventListener('click',signUp);$('signinButton').addEventListener('click',signIn);$('resetButton').addEventListener('click',resetPassword);
  $('guestButton').addEventListener('click',async()=>{if(await ensureGuest()){currentToken='';showWorkspace({account:false});message('guestMsg','Guest session ready. Nothing was saved to an account.','success');}});
  $('signout').addEventListener('click',signOut);$('image').addEventListener('change',()=>setFile($('image').files[0]));$('clearButton').addEventListener('click',clearLocalFile);$('analyzeButton').addEventListener('click',runAnalysis);$('downloadButton').addEventListener('click',downloadReport);$('deleteButton').addEventListener('click',deleteJob);
  document.querySelectorAll('[data-heatmap]').forEach(b=>b.addEventListener('click',()=>setMetric(b.dataset.heatmap)));
  $('clearROI')?.addEventListener('click',()=>{roi=null;drawCanvas();$('roiSummary').textContent='Draw a rectangle on the viewer to inspect a spatial subset.';});
  $('analysisCanvas') && setupROI();
  if(authReady){
    supa=window.supabase.createClient(cfg.supabaseUrl,cfg.supabasePublishableKey,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true}});
    supa.auth.onAuthStateChange((_event,session)=>{currentToken=session?.access_token||'';if(session){guestToken='';showWorkspace({account:true});}});
    supa.auth.getSession().then(({data})=>{currentToken=data.session?.access_token||'';if(data.session)showWorkspace({account:true});});
  } else setAccessMode('guest');
})();
