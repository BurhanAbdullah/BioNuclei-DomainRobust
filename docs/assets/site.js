document.addEventListener('DOMContentLoaded', function () {
  /* Shared visual layer, loaded consistently on every research page. */
  if (!document.querySelector('link[data-bionuclei-enhancements]')) {
    var styleLink = document.createElement('link');
    styleLink.rel = 'stylesheet';
    styleLink.href = 'assets/enhancements.css';
    styleLink.setAttribute('data-bionuclei-enhancements', 'true');
    document.head.appendChild(styleLink);
  }

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

  /* Keep visible editorial copy clean. Code, SVG and scripts are untouched. */
  var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  var textNodes = [];
  while (walker.nextNode()) textNodes.push(walker.currentNode);
  textNodes.forEach(function (node) {
    var parent = node.parentElement;
    if (!parent || /^(SCRIPT|STYLE|CODE|PRE|SVG)$/i.test(parent.tagName)) return;
    node.nodeValue = node.nodeValue.replace(/\s*[→←]\s*/g, ' ').replace(/\s*[—–]\s*/g, ' ').replace(/\s{2,}/g, ' ');
  });

  /* Homepage Explore section: dynamic filters without changing the underlying research content. */
  var featureGrid = document.querySelector('.landing-feature .feature-grid');
  if (featureGrid && !featureGrid.dataset.enhanced) {
    featureGrid.dataset.enhanced = 'true';
    var categoryMap = {
      'Vision': 'science architecture',
      'Architecture': 'architecture',
      'Research': 'science',
      'BioMCP': 'architecture ecosystem',
      'People': 'community',
      'Community': 'community'
    };
    var cards = Array.prototype.slice.call(featureGrid.querySelectorAll('.feature-card'));
    cards.forEach(function (card) {
      var title = card.querySelector('h3');
      var name = title ? title.textContent.trim() : '';
      card.dataset.category = categoryMap[name] || 'science';
    });
    var toolbar = document.createElement('div');
    toolbar.className = 'explore-toolbar';
    toolbar.setAttribute('role', 'toolbar');
    toolbar.setAttribute('aria-label', 'Filter project layers');
    ['All', 'Science', 'Architecture', 'Ecosystem', 'Community'].forEach(function (label, index) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = 'explore-filter' + (index === 0 ? ' active' : '');
      button.dataset.filter = label.toLowerCase();
      button.setAttribute('aria-pressed', index === 0 ? 'true' : 'false');
      button.textContent = label;
      toolbar.appendChild(button);
    });
    var meta = document.createElement('div');
    meta.className = 'explore-meta';
    meta.innerHTML = '<span data-explore-count></span><span>Interactive project map</span>';
    featureGrid.parentNode.insertBefore(toolbar, featureGrid);
    featureGrid.parentNode.insertBefore(meta, featureGrid);

    function applyExploreFilter(filter) {
      var shown = 0;
      cards.forEach(function (card) {
        var categories = (card.dataset.category || '').split(/\s+/);
        var visible = filter === 'all' || categories.indexOf(filter) !== -1;
        card.classList.toggle('is-filtered', !visible);
        if (visible) shown += 1;
      });
      var count = meta.querySelector('[data-explore-count]');
      if (count) count.textContent = shown + ' of ' + cards.length + ' sections shown';
      toolbar.querySelectorAll('.explore-filter').forEach(function (button) {
        var active = button.dataset.filter === filter;
        button.classList.toggle('active', active);
        button.setAttribute('aria-pressed', active ? 'true' : 'false');
      });
    }
    toolbar.querySelectorAll('.explore-filter').forEach(function (button) {
      button.addEventListener('click', function () { applyExploreFilter(button.dataset.filter); });
    });
    applyExploreFilter('all');
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
    document.querySelectorAll('.card,.feature-card,.team-card,.research-card,.metric,.process-card,.diagram-panel,.landing-intro-grid,.landing-research-grid').forEach(function (el) {
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
          var safeLogin = p.login.replace(/[&<>"']/g, '');
          var safeAvatar = String(p.avatar_url || '').replace(/"/g, '%22');
          var safeUrl = String(p.html_url || '').replace(/"/g, '%22');
          card.innerHTML = '<img class="team-avatar" src="' + safeAvatar + '" alt="GitHub contributor avatar" loading="lazy"><div class="team-info"><h3>' + safeLogin + '</h3><p>GitHub contributor</p><a class="team-link" href="' + safeUrl + '">View contribution profile</a></div>';
          contributors.appendChild(card);
        });
      }).catch(function () {});
  }
});
