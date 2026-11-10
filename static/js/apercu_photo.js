// Fenêtre d'aperçu : un clic sur une photo (lien .apercu-photo) l'ouvre en grand dans la page.
(function () {
  function ouvrir(src, titre) {
    const fond = document.createElement('div');
    fond.className = 'apercu-fond';
    fond.innerHTML =
      '<div class="apercu-boite" role="dialog" aria-modal="true" aria-label="Aperçu de la photo">' +
      '<button type="button" class="apercu-fermer" aria-label="Fermer">&times;</button>' +
      '<img alt="' + (titre || 'Photo') + '">' +
      '</div>';
    fond.querySelector('img').src = src;
    document.body.appendChild(fond);

    function fermer() {
      document.removeEventListener('keydown', surTouche);
      fond.remove();
    }
    function surTouche(e) { if (e.key === 'Escape') fermer(); }
    fond.addEventListener('click', function (e) { if (e.target === fond) fermer(); });
    fond.querySelector('.apercu-fermer').addEventListener('click', fermer);
    document.addEventListener('keydown', surTouche);
  }

  document.addEventListener('click', function (e) {
    const lien = e.target.closest('a.apercu-photo');
    if (!lien) return;
    e.preventDefault();
    ouvrir(lien.getAttribute('href'), lien.dataset.titre);
  });
})();
