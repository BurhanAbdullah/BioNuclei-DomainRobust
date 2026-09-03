document.addEventListener('DOMContentLoaded', function () {
  var links = document.querySelector('.nav-links');
  var toggle = document.querySelector('.nav-toggle');
  var path = window.location.pathname.split('/').pop() || 'index.html';

  if (links) {
    var navItems = [['vision.html','Vision'],['research.html','Research'],['bionuclei.html','BioNuclei'],['datasets.html','Datasets'],['architecture.html','Architecture'],['biomcp.html','BioMCP'],['biofm.html','BioFM'],['biowf.html','BioWF'],['bioskills.html','BioSkills'],['team.html','People'],['community.html','Community']];
    links.innerHTML = navItems.map(function(item){return '<a href="'+item[0]+'">'+item[1]+'</a>';}).join('');
    links.querySelectorAll('a').forEach(function(a){
      if ((a.getAttribute('href')||'').split('#')[0].split('/').pop() === path) a.classList.add('active');
    });
  }

  var brand = document.querySelector('.brand');
  if (brand) {
    var mark = brand.querySelector('.mark');
    if (mark && mark.tagName.toLowerCase() !== 'img') {
      var image = document.createElement('img'); image.src='assets/logo-mark.svg'; image.className='mark'; image.alt='BioNuclei'; mark.replaceWith(image);
    }
    var name = brand.querySelector('span:not(.mark)');
    if (name) name.innerHTML='BioNuclei<small>Research for robust bioimaging AI</small>';
  }

  if (!document.getElementById('bionuclei-site-audit')) {
    var style=document.createElement('style'); style.id='bionuclei-site-audit';
    style.textContent='@media(max-width:900px){.nav-inner{position:relative;flex-wrap:wrap}.nav-toggle{display:inline-flex}.nav-links{display:none;width:100%;order:3;flex-direction:column;align-items:stretch;gap:0;padding:10px 0 16px;border-top:1px solid #D7D2CB;background:#fff}.nav-links.open{display:flex}.nav-links a{padding:10px 4px;border-bottom:1px solid #D7D2CB}.nav-cta{margin-left:auto}}\n.section.soft{padding:110px 0;background:var(--cream);border-block:1px solid var(--line)}\n.wrap.soft{padding:36px}\n.section.dark .card,.section.dark .feature,.section.dark .research-card,.section.dark .metric,.section.dark .process-card,.section.dark .node,.section.dark .diagram-panel,.section.dark .team-card{background:#fff!important;color:var(--ink)!important}\n.section.dark .card h3,.section.dark .card p,.section.dark .feature h3,.section.dark .feature p,.section.dark .research-card h3,.section.dark .research-card p,.section.dark .metric h3,.section.dark .metric p,.section.dark .process-card h3,.section.dark .process-card p,.section.dark .team-card h3,.section.dark .team-card p{color:var(--ink)!important}\n.section.dark .card .kicker,.section.dark .feature .kicker,.section.dark .research-card .status,.section.dark .metric .tag,.section.dark .process-card .program-num{color:var(--harvard)!important}\n.card,.feature,.research-card,.metric,.process-card,.team-card{transition:transform .22s ease,box-shadow .22s ease,border-color .22s ease}.card:hover,.feature:hover,.research-card:hover,.metric:hover,.process-card:hover,.team-card:hover{transform:translateY(-3px);box-shadow:0 12px 28px rgba(30,30,30,.10);border-color:#b7aaa0}\n.card:focus-within,.feature:focus-within,.research-card:focus-within,.process-card:focus-within{outline:2px solid var(--harvard);outline-offset:3px}\n@media(prefers-reduced-motion:reduce){.card,.feature,.research-card,.metric,.process-card,.team-card{transition:none!important}}';
    document.head.appendChild(style);
  }

  if (toggle && links) {
    toggle.setAttribute('aria-expanded','false');
    toggle.addEventListener('click',function(){var open=links.classList.toggle('open');toggle.setAttribute('aria-expanded',open?'true':'false');toggle.setAttribute('aria-label',open?'Close navigation':'Open navigation');});
    links.addEventListener('click',function(e){if(e.target.tagName.toLowerCase()==='a'){links.classList.remove('open');toggle.setAttribute('aria-expanded','false');}});
  }

  document.querySelectorAll('[data-year]').forEach(function(el){el.textContent=new Date().getFullYear();});

  document.querySelectorAll('.card,.feature,.research-card,.process-card,.team-card,.section-head').forEach(function(el){
    if (!el.classList.contains('reveal')) el.classList.add('site-reveal');
  });
  if (!document.getElementById('bionuclei-reveal-style')) {
    var revealStyle=document.createElement('style'); revealStyle.id='bionuclei-reveal-style';
    revealStyle.textContent='.site-reveal{opacity:0;transform:translateY(18px);transition:opacity .55s ease,transform .55s ease}.site-reveal.site-visible{opacity:1;transform:none}@media(prefers-reduced-motion:reduce){.site-reveal{opacity:1!important;transform:none!important;transition:none!important}}';
    document.head.appendChild(revealStyle);
  }
  var reveals=document.querySelectorAll('.site-reveal');
  if ('IntersectionObserver' in window) {
    var observer=new IntersectionObserver(function(entries){entries.forEach(function(entry){if(entry.isIntersecting){entry.target.classList.add('site-visible');observer.unobserve(entry.target);}});},{threshold:.08});
    reveals.forEach(function(el){observer.observe(el);});
  } else reveals.forEach(function(el){el.classList.add('site-visible');});

  var contributors=document.querySelector('[data-contributors]');
  if (!contributors) return;
  fetch('https://api.github.com/repos/BurhanAbdullah/BioNuclei-DomainRobust/contributors?per_page=100')
    .then(function(r){return r.ok?r.json():[];})
    .then(function(items){
      var people=items.filter(function(p){return p.type==='User'&&p.login.toLowerCase()!=='burhanabdullah'&&!/bot$/i.test(p.login)&&!/\[bot\]/i.test(p.login);});
      if(!people.length){contributors.innerHTML='<p class="feature">No additional public repository contributors are currently listed.</p>';return;}
      people.forEach(function(p){
        var card=document.createElement('article'); card.className='team-card';
        var image=document.createElement('img'); image.className='team-avatar'; image.src=p.avatar_url; image.alt='GitHub contributor avatar'; image.loading='lazy';
        var info=document.createElement('div'); info.className='team-info';
        var name=document.createElement('h3'); name.textContent=p.login;
        var role=document.createElement('p'); role.textContent='GitHub contributor';
        var profile=document.createElement('a'); profile.className='team-link'; profile.href=p.html_url; profile.textContent='View contribution profile';
        info.appendChild(name);info.appendChild(role);info.appendChild(profile);card.appendChild(image);card.appendChild(info);contributors.appendChild(card);
      });
    }).catch(function(){contributors.innerHTML='<p class="feature">Public contributor profiles could not be loaded right now. The project lead and repository remain available above.</p>';});
});