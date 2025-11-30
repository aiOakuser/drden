from django.shortcuts import redirect, render

from .forms import FashionConsultLeadForm


def home(request):
    if request.method == "POST":
        form = FashionConsultLeadForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("marketing:popup_thank_you")
    else:
        form = FashionConsultLeadForm()

    return render(request, "marketing/home.html", {"form": form})


def popup_thank_you(request):
    return render(request, "marketing/thank_you.html")
