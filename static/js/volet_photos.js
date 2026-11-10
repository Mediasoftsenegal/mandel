// Volet d'aperçu : un clic sur une miniature affiche la photo en grand dans le volet.
// Consultation uniquement : aucun appel serveur, le score n'est pas modifié.
(function () {
  const grande = document.getElementById('photo-grande');
  const miniatures = document.querySelectorAll('.volet .miniature[data-src]');
  if (!grande || !miniatures.length) return;
  miniatures.forEach(function (bouton) {
    bouton.addEventListener('click', function () {
      grande.src = bouton.dataset.src;
      miniatures.forEach(function (b) { b.classList.toggle('active', b === bouton); });
    });
  });
})();
