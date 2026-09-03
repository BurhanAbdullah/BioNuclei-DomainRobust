document.addEventListener('DOMContentLoaded', function () {
  var nav = document.querySelector('.site-nav');
  var toggle = document.querySelector('.nav-toggle');
  var links = document.querySelector('.nav-links');

  /* Keep one canonical information architecture across every page. */
  if (links) {
    links.innerHTML = [
      ['vision.html', 'Vision'],
      ['research.html', 'Research'],
      ['bionuclei.html', 'BioNuclei'],
      ['datasets.html', 'Datasets'],
      ['architecture.html', 'Architecture'],
      ['biomcp.html', 'BioMCP'],
      ['biofm.html', 'BioFM'],
      ['biowf.html', 'BioWF'],
      ['bioskills.html', 'BioSkills'],
      ['team.html', 'People'],
      ['community.html', 'Community']
    ].map(function (item) {
      return '<a href="' + item[0] + '">' + item[1] + '</a>';
    }).join('');
  }

  /* Repair legacy pages that still contain the old empty mark. */
  var brand = document.querySelector('.brand');
  if (brand) {
    var mark = brand.querySelector('.mark');
    if (mark && mark.tagName.toLowerCase() !== 'img') {
      var image = document.createElement('img');
      image.src = 'assets/logo-mark.svg';
      image.className = 'mark';
      image.alt = 'BioNuclei';
      mark.replaceWith(image);
    }
    var brandName = brand.querySelector('span:not(.mark)');
    if (brandName) {
      brandName.innerHTML = 'BioNuclei<small>Research for robust bioimaging AI</small>';
    }
  }

  /* Mobile navigation: the shared CSS may be cached independently, so keep the
     required open state here as a small progressive enhancement. */
  if (!document.getElementById('bionuclei-mobile-nav')) {
    var style = document.createElement('style');
    style.id = 'bionuclei-mobile-nav';
    style.textContent = '@media (max-width:900px){.nav-inner{position:relative;flex-wrap:wrap}.nav-toggle{display:inline-flex}.nav-links{display:none;width:100%;order:3;flex-direction:column;align-items:stretch;gap:0;padding:10px 0 16px;border-top:1px solid #D7D2CB;background:#fff}.nav-links.open{display:flex}.nav-links a{padding:10px 4px;border-bottom:1px solid #D7D2CB}.nav-cta{margin-left:auto}}';
    document.head.appendChild(style);
  }

  if (toggle && links) {
    toggle.setAttribute('aria-expanded', 'false');
    toggle.addEventListener('click', function () {
      var open = links.classList.toggle('open');
      toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
      toggle.setAttribute('aria-label', open ? 'Close navigation' : 'Open navigation');
    });
    links.addEventListener('click', function (event) {
      if (event.target.tagName.toLowerCase() === 'a') {
        links.classList.remove('open');
        toggle.setAttribute('aria-expanded', 'false');
        toggle.setAttribute('aria-label', 'Open navigation');
      }
    });
  }

  var path = window.location.pathname.split('/').pop() || 'index.html';
  document.querySelectorAll('.nav-links a').forEach(function (a) {
    var href = (a.getAttribute('href') || '').split('#')[0].split('/').pop();
    if (href === path || (path === '' && href === 'index.html')) {
      a.classList.add('active');
    }
  });

  document.querySelectorAll('[data-year]').forEach(function (el) {
    el.textContent = new Date().getFullYear();
  });

  var contributors = document.querySelector('[data-contributors]');
  if (!contributors) return;

  fetch('https://api.github.com/repos/BurhanAbdullah/BioNuclei-DomainRobust/contributors?per_page=100')
    .then(function (response) {
      return response.ok ? response.json() : [];
    })
    .then(function (items) {
      var people = items.filter(function (person) {
        return person.type === 'User' &&
          person.login.toLowerCase() !== 'burhanabdullah' &&
          !/bot$/i.test(person.login) &&
          !/\[bot\]/i.test(person.login);
      });

      if (!people.length) {
        contributors.innerHTML = '<p class="feature">No additional public repository contributors are currently listed.</p>';
        return;
      }

      people.forEach(function (person) {
        var card = document.createElement('article');
        card.className = 'team-card';

        var image = document.createElement('img');
        image.className = 'team-avatar';
        image.src = person.avatar_url;
        image.alt = 'GitHub contributor avatar';
        image.loading = 'lazy';

        var info = document.createElement('div');
        info.className = 'team-info';

        var name = document.createElement('h3');
        name.textContent = person.login;

        var role = document.createElement('p');
        role.textContent = 'GitHub contributor';

        var profile = document.createElement('a');
        profile.className = 'team-link';
        profile.href = person.html_url;
        profile.textContent = 'View contribution profile';

        info.appendChild(name);
        info.appendChild(role);
        info.appendChild(profile);
        card.appendChild(image);
        card.appendChild(info);
        contributors.appendChild(card);
      });
    })
    .catch(function () {
      contributors.innerHTML = '<p class="feature">Public contributor profiles could not be loaded right now. The project lead and repository remain available above.</p>';
    });
});
