from django.db import models


class FashionConsultLead(models.Model):
    full_name = models.CharField(max_length=150)
    phone_number = models.CharField(max_length=20)
    country_code = models.CharField(max_length=5, default="+1")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.country_code}{self.phone_number})"
