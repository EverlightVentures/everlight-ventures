from django.core.management.base import BaseCommand

from business_os.services import refresh_business_os


class Command(BaseCommand):
    help = "Refresh Business OS stream metrics and snapshot data."

    def handle(self, *args, **options):
        refresh_business_os()
        self.stdout.write(self.style.SUCCESS("Business OS refreshed"))

