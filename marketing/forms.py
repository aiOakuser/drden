from django import forms

from .models import FashionConsultLead


class FashionConsultLeadForm(forms.ModelForm):
    class Meta:
        model = FashionConsultLead
        fields = ["full_name", "country_code", "phone_number"]
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "placeholder": "Enter your full name",
                    "class": "popup-input",
                }
            ),
            "country_code": forms.TextInput(
                attrs={
                    "value": "+1",
                    "class": "popup-country-code",
                }
            ),
            "phone_number": forms.TextInput(
                attrs={
                    "placeholder": "Phone number",
                    "class": "popup-phone-input",
                }
            ),
        }
