document.addEventListener('DOMContentLoaded', function () {
  var target = document.querySelector('[data-community-members]');
  if (!target) return;
  fetch('community-members.json', {cache:'no-store'})
    .then(function (r) { return r.ok ? r.json() : {members:[]}; })
    .then(function (data) {
      var members = Array.isArray(data.members) ? data.members : [];
      if (!members.length) {
        target.innerHTML = '<article class="team-card"><div class="team-info"><h3>No community members yet</h3><p>Be the first to join through the Community page.</p><a class="team-link" href="community.html">Join with GitHub</a></div></article>';
        return;
      }
      target.innerHTML = '';
      members.forEach(function (member) {
        var login = member.github;
        var card = document.createElement('article');
        card.className = 'team-card';
        var image = document.createElement('img');
        image.className = 'team-avatar';
        image.src = 'https://github.com/' + encodeURIComponent(login) + '.png?size=180';
        image.alt = 'GitHub profile avatar';
        image.loading = 'lazy';
        var info = document.createElement('div');
        info.className = 'team-info';
        var name = document.createElement('h3');
        name.textContent = login;
        var role = document.createElement('p');
        role.textContent = 'BioNuclei community member';
        var profile = document.createElement('a');
        profile.className = 'team-link';
        profile.href = member.profile || ('https://github.com/' + login);
        profile.textContent = 'GitHub profile';
        info.appendChild(name); info.appendChild(role); info.appendChild(profile);
        card.appendChild(image); card.appendChild(info); target.appendChild(card);
      });
    })
    .catch(function () {
      target.innerHTML = '<article class="team-card"><div class="team-info"><h3>Community registry unavailable</h3><p>Please try again shortly.</p></div></article>';
    });
});
