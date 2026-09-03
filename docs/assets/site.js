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
      items
        .filter(function (person) {
          return person.type === 'User' &&
            person.login.toLowerCase() !== 'burhanabdullah' &&
            !/bot$/i.test(person.login) &&
            !/\[bot\]/i.test(person.login);
        })
        .forEach(function (person) {
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
      /* The people page remains usable when the public API is unavailable. */
    });
});
