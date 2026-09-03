document.addEventListener('DOMContentLoaded', function () {
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');
  if (toggle && links) {
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
          card.innerHTML = '<img class="team-avatar" src="' + p.avatar_url + '" alt="GitHub contributor avatar" loading="lazy"><div class="team-info"><h3>' + p.login.replace(/[&<>]/g, '') + '</h3><p>GitHub contributor</p><a class="team-link" href="' + p.html_url + '">View contribution profile</a></div>';
          contributors.appendChild(card);
        });
      }).catch(function () {});
  }
});
