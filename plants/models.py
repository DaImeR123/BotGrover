from django.db import models
from django.utils import timezone
from datetime import timedelta


class Culture(models.Model):
    name = models.CharField("Название", max_length=100)
    grow_days = models.IntegerField("Срок созревания (дни)")
    expire_days = models.IntegerField("Срок годности (дни)")
    grams_per_tray = models.IntegerField("Грамм на лоток", default=0)
    soaking_required = models.BooleanField("Замачивание", default=False)
    press_weight = models.CharField(
        "Прижим (кг)",
        max_length=10,
        choices=[("0.5", "0.5 кг"), ("1", "1 кг")],
        default="0.5"
    )
    germination_days = models.IntegerField("Дней на прорастание (20°C)", default=3)
    light_days = models.IntegerField("Дней на свету", default=5)

    def __str__(self):
        return self.name


class Planting(models.Model):
    STATUS_CHOICES = [
        ('growing', 'Растет'),
        ('ready', 'Созрело'),
        ('expired', 'Просрочено')
    ]

    culture = models.ForeignKey(Culture, on_delete=models.CASCADE, verbose_name="Культура")
    plant_date = models.DateField("Дата посадки", default=timezone.now)
    quantity = models.IntegerField("Количество")
    harvest_date = models.DateField("Дата созревания", blank=True, null=True)
    sale_deadline = models.DateField("Крайний срок продажи", blank=True, null=True)
    status = models.CharField("Статус", max_length=10, choices=STATUS_CHOICES, default='growing')

    def save(self, *args, **kwargs):
        self.harvest_date = self.plant_date + timedelta(days=self.culture.grow_days)
        self.sale_deadline = self.harvest_date + timedelta(days=self.culture.expire_days)

        today = timezone.now().date()
        if today >= self.sale_deadline:
            self.status = 'expired'
        elif today >= self.harvest_date:
            self.status = 'ready'
        else:
            self.status = 'growing'

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.culture} - {self.plant_date.strftime('%Y-%m-%d')}"