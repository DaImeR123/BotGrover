from django.core.management.base import BaseCommand
from django.utils import timezone
from plants.models import Planting

class Command(BaseCommand):
    help = 'Обновляет статусы всех посадок'

    def handle(self, *args, **options):
        today = timezone.now().date()
        plantings = Planting.objects.all()

        for planting in plantings:
            if today >= planting.expire_date:
                planting.status = 'expired'
            elif today >= planting.harvest_date:
                planting.status = 'ready'
            else:
                planting.status = 'growing'
            planting.save()

        self.stdout.write("Статусы обновлены!")