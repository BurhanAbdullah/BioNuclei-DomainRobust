document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
    toggle.setAttribute('aria-expanded', 'false');
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    links.querySelectorAll('a').forEach(function (a) {
      a.addEventListener('click', function () {
        links.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  var path = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(function (a) {
    var href = (a.getAttribute('href') || '').split('#')[0].split('/').pop();
    if (href === path || (path === '' && href === 'index.html')) a.classList.add('active');
  });

  document.querySelectorAll('[data-year]').forEach(function (el) {
    el.textContent = new Date().getFullYear();
  });

  /* Keep visible editorial copy clean and consistent. Code, SVG and scripts are untouched. */
  var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  var textNodes = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode);
  textNodes.forEach(function (node) {
    var parent = node.parentElement;
    if (!parent || /^(SCRIPT|STYLE|CODE|PRE|SVG)$/i.test(parent.tagName)) return;
    node.nodeValue = node.nodeValue.replace(/\s*[→←]\s*/g, ' ').replace(/\s*[—–]\s*/g, ' ').replace(/\s{2,}/g, ' ');
  });

  /* Homepage explorer. */
  var explorer = document.querySelector('[data-explorer]');
  if (explorer) {
    var cards = Array.prototype.slice.call(explorer.querySelectorAll('[data-category]'));
    var buttons = explorer.querySelectorAll('[data-filter]');
    var count = explorer.querySelector('[data-count]');
    function applyFilter(filter) {
      var visible = 0;
      cards.forEach(function (card) {
        var show = filter === 'all' || (card.getAttribute('data-category') || '').split(' ').indexOf(filter) !== -1;
        card.hidden = !show;
        if (show) visible += 1;
      });
      buttons.forEach(function (button) {
        var active = button.getAttribute('data-filter') === filter;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
      if (count) count.textContent = visible + ' of ' + cards.length + ' layers shown';
    }
    buttons.forEach(function (button) {
      button.addEventListener('click', function () { applyFilter(button.getAttribute('data-filter')); });
    });
    applyFilter('all');
  }

  /* Single source of truth for the public Bio* research map. Status labels describe research maturity, not scientific validity. */
  var projects = [
    { name: 'BioNuclei', type: 'Scientific foundation', status: 'Active research', category: 'science', description: 'Domain-robust nuclear instance segmentation, reproducible evaluation, failure analysis and external validation.', href: 'research.html' },
    { name: 'BioMCP', type: 'Interoperability layer', status: 'Architecture / prototyping', category: 'architecture', description: 'Typed interfaces connecting AI agents with established bioimaging tools, models, workflows and provenance.', href: 'biomcp.html' },
    { name: 'BioFM', type: 'Foundation-model research', status: 'Research direction', category: 'ecosystem', description: 'Domain-aware vision and multimodal foundation-model research for biological imaging.', href: 'biofm.html' },
    { name: 'BioWF', type: 'Workflow layer', status: 'Design / research direction', category: 'ecosystem', description: 'Versioned, reproducible and auditable composition and execution of scientific imaging workflows.', href: 'biowf.html' },
    { name: 'BioSkills', type: 'Scientific knowledge layer', status: 'Design / research direction', category: 'ecosystem', description: 'Reusable scientific procedures, validation rules, failure analysis and domain guidance for agents and workflows.', href: 'bioskills.html' }
  ];

  var registry = document.querySelector('[data-project-registry]');
  if (registry) {
    projects.forEach(function (project) {
      var card = document.createElement('article');
      card.className = 'research-card';
      card.setAttribute('data-project', project.name.toLowerCase());
      card.innerHTML = '<span class="status progress">' + project.status + '</span>' +
        '<p class="kicker">' + project.type + '</p>' +
        '<h3><a href="' + project.href + '">' + project.name + '</a></h3>' +
        '<p>' + project.description + '</p>' +
        '<a class="text-link" href="' + project.href + '">Open project</a>';
      registry.appendChild(card);
    });
  }

  if ('IntersectionObserver' in window) {
    var observer = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });
    document.querySelectorAll('.card,.feature-card,.team-card,.research-card,.metric,.process-card,.diagram-panel,.landing-intro-grid,.landing-research-grid,.explore-toolbar').forEach(function (el) {
      el.classList.add('reveal');
      observer.observe(el);
    });
  }

  var contributors = document.querySelector('[data-contributors]');
  if (contributors) {
    fetch('https://api.github.com/repos/BurhanAbdullah/BioNuclei-DomainRobust/contributors?per_page=100')
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (items) {
        var people = items.filter(function (p) {
          return p.type === 'User' && p.login.toLowerCase() !== 'burhanabdullah' && !/bot$/i.test(p.login) && !/\[bot\]/i.test(p.login);
        });
        people.forEach(function (p) {
          var card = document.createElement('article');
          card.className = 'team-card reveal is-visible';
          var img = document.createElement('img'); img.className = 'team-avatar'; img.src = p.avatar_url; img.alt = 'GitHub contributor avatar'; img.loading = 'lazy';
          var info = document.createElement('div'); info.className = 'team-info';
          var name = document.createElement('h3'); name.textContent = p.login;
          var role = document.createElement('p'); role.textContent = 'GitHub contributor';
          var link = document.createElement('a'); link.className = 'team-link'; link.href = p.html_url; link.textContent = 'View contribution profile';
          info.appendChild(name); info.appendChild(role); info.appendChild(link); card.appendChild(img); card.appendChild(info); contributors.appendChild(card);
        });
      }).catch(function () {});
  }
});
