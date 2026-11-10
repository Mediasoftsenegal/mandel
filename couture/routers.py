class LegacyRouter:
    """Route les modèles de l'app `couture` vers la base MySQL existante (`legacy`).

    Django interne (auth, sessions, admin) reste sur `default`.
    Aucune migration n'est jamais appliquée sur `legacy` : les tables existent déjà
    et sont gérées par l'application PHP pendant la transition.
    """

    APP = 'couture'

    def db_for_read(self, model, **hints):
        return 'legacy' if model._meta.app_label == self.APP and 'legacy' in self._aliases() else None

    def db_for_write(self, model, **hints):
        return 'legacy' if model._meta.app_label == self.APP and 'legacy' in self._aliases() else None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if db == 'legacy':
            return False
        if app_label == self.APP:
            return False  # les modèles couture sont managed=False
        return None

    @staticmethod
    def _aliases():
        from django.conf import settings
        return settings.DATABASES
