(function(){
'use strict';
const fileInput=document.getElementById('file'),stage=document.getElementById('stage');
if(!fileInput||!stage)return;
const hint=document.createElement('div');hint.className='lab-drop-hint';hint.innerHTML='<strong>Drop a microscopy file here</strong><span>TIFF / TIF or ND2 · preview stays in this browser</span>';
stage.appendChild(hint);
const toolbar=document.createElement('div');toolbar.className='lab-tools';
toolbar.innerHTML='<button type="button" class="btn small" id="lab-clear" disabled>Clear selection</button><span id="lab-file-note" aria-live="polite">Local preview only. Your file is not uploaded here.</span>';
stage.parentNode.insertBefore(toolbar,stage.nextSibling);
const clear=document.getElementById('lab-clear'),note=document.getElementById('lab-file-note');
function accepted(f){return f&&(/\.(tif|tiff|nd2)$/i.test(f.name));}
function choose(f){if(!accepted(f)){note.textContent='Unsupported file. Choose TIFF/TIF or ND2.';return;}const dt=new DataTransfer();dt.items.add(f);fileInput.files=dt.files;fileInput.dispatchEvent(new Event('change',{bubbles:true}));clear.disabled=false;hint.classList.remove('active');note.textContent=f.name+' selected. Local preview only.';}
['dragenter','dragover'].forEach(ev=>stage.addEventListener(ev,e=>{e.preventDefault();hint.classList.add('active');}));
['dragleave','dragend'].forEach(ev=>stage.addEventListener(ev,e=>{if(!stage.contains(e.relatedTarget))hint.classList.remove('active');}));
stage.addEventListener('drop',e=>{e.preventDefault();hint.classList.remove('active');const f=e.dataTransfer&&e.dataTransfer.files&&e.dataTransfer.files[0];if(f)choose(f);});
clear.addEventListener('click',()=>{fileInput.value='';const im=document.getElementById('image');im.hidden=true;im.removeAttribute('src');document.getElementById('empty').hidden=false;document.getElementById('empty').textContent='Choose or drop an ND2 or TIFF file.';['fileTitle','format','size','shape'].forEach(id=>document.getElementById(id).textContent=id==='fileTitle'?'No image selected':'Not selected');document.getElementById('fileMeta').textContent='Supported inputs: Nikon ND2 and TIFF/TIF';document.getElementById('manualBtn').disabled=true;clear.disabled=true;note.textContent='Local preview only. Your file is not uploaded here.';hint.classList.remove('active');if(window.__bionucleiLabRevoke)window.__bionucleiLabRevoke();});
fileInput.addEventListener('change',()=>{const f=fileInput.files&&fileInput.files[0];if(f&&accepted(f)){clear.disabled=false;note.textContent=f.name+' selected. Local preview only.';}});
})();