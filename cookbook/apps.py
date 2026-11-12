from django.apps import AppConfig

# Commands that must never trigger the automatic schema/seed healing.
SKIP_COMMANDS = {
    "test",
    "migrate",
    "makemigrations",
    "seed",
    "seed_demo",
    "collectstatic",
    "shell",
    "dbshell",
    "loaddata",
    "dumpdata",
    "createsuperuser",
    "check",
}

MIGRATE_ATTEMPTED = False


def running_tests():
    """True under `manage.py test` and under pytest (which the CI may prefer)."""
    import os
    import sys

    if "test" in sys.argv:
        return True
    if "pytest" in sys.modules:
        return True
    return any("pytest" in os.path.basename(arg) for arg in sys.argv[:2])


class CookbookConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "cookbook"
    verbose_name = "Ladle Kitchen Cookbook"

    def ready(self):
        # A warm container can reach `runserver` without install.sh having run,
        # leaving an empty or unmigrated SQLite file behind. The first request
        # heals it (migrate, then the idempotent seed) instead of serving 500s or
        # empty pages. It runs on `request_started`, not here, so nothing queries
        # the database during app initialisation.
        import sys

        if len(sys.argv) > 1 and sys.argv[1] in SKIP_COMMANDS:
            return
        if running_tests():
            return

        from django.core.signals import request_started

        request_started.connect(
            self.prepare_database_once, dispatch_uid="cookbook.prepare_database_once"
        )

    def prepare_database_once(self, sender, **kwargs):
        global MIGRATE_ATTEMPTED

        from django.core.signals import request_started
        from django.db import connection

        try:
            tables = connection.introspection.table_names()
        except Exception:  # database not reachable yet — a later request retries
            return

        if "cookbook_recipe" not in tables and not MIGRATE_ATTEMPTED:
            MIGRATE_ATTEMPTED = True
            self.run_migrations()
            try:
                tables = connection.introspection.table_names()
            except Exception:
                return

        if "cookbook_recipe" not in tables:
            return

        request_started.disconnect(dispatch_uid="cookbook.prepare_database_once")
        self.seed_demo_now()

    def run_migrations(self):
        from django.core.management import call_command

        try:
            call_command("migrate", interactive=False, verbosity=0)
        except Exception:
            # Never take the server down; report it and let the next request try.
            import traceback

            traceback.print_exc()

    def seed_demo_now(self):
        from django.core.management import call_command

        try:
            call_command("seed_demo", quiet=True, verbosity=0)
        except Exception:
            import traceback

            traceback.print_exc()
