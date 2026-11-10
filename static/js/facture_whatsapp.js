// Envoi de la facture par WhatsApp, sans impression.
// Sur téléphone : feuille de partage native, le PDF est joint directement.
// Sur ordinateur : téléchargement du PDF, puis ouverture de WhatsApp avec le texte prérempli.
(function () {
  const bouton = document.getElementById('envoyer-whatsapp');
  const donnees = document.getElementById('donnees-whatsapp');
  if (!bouton || !donnees) return;
  const d = JSON.parse(donnees.textContent);

  if (!d.telephone_valide) {
    bouton.disabled = true;
    bouton.title = 'Numéro de téléphone manquant ou invalide';
  }

  bouton.addEventListener('click', async function () {
    bouton.disabled = true;
    try {
      const reponse = await fetch(d.pdf_url, { credentials: 'same-origin' });
      if (!reponse.ok) throw new Error('PDF introuvable (' + reponse.status + ')');
      const blob = await reponse.blob();
      const fichier = new File([blob], d.nom_fichier, { type: 'application/pdf' });

      if (navigator.canShare && navigator.canShare({ files: [fichier] })) {
        try {
          await navigator.share({ files: [fichier], text: d.texte, title: d.titre });
          return;
        } catch (e) {
          if (e.name === 'AbortError') return;
        }
      }

      // Repli (ordinateur) : téléchargement du PDF, puis WhatsApp avec le texte.
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = d.nom_fichier;
      a.click();
      URL.revokeObjectURL(url);
      if (d.lien) window.open(d.lien, '_blank', 'noopener');
      alert("Le PDF a été téléchargé. Joignez-le dans la conversation WhatsApp qui vient de s'ouvrir.");
    } catch (e) {
      alert('Envoi impossible : ' + e.message);
    } finally {
      bouton.disabled = !d.telephone_valide;
    }
  });
})();
