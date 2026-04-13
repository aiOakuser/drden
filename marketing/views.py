from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import FashionConsultLeadForm
from .social_regenerator import regenerate_bundle


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


@login_required
@require_http_methods(["GET", "POST"])
def social_content_dashboard(request):
    """
    Staff-only: view latest saved bundles and trigger regeneration (copy-paste to Meta / LinkedIn / X).
    """
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied()

    from marketing.models import SocialContentBundle

    message = ""
    if request.method == "POST" and request.POST.get("action") == "regenerate":
        bundle = regenerate_bundle(save=True)
        if bundle.success:
            message = f"Regenerated and saved (bundle #{bundle.pk})."
        else:
            message = f"Regeneration failed: {bundle.error[:500]}"

    latest = SocialContentBundle.objects.order_by("-created_at")[:12]
    current = latest[0] if latest else None
    return render(
        request,
        "marketing/social_content_dashboard.html",
        {
            "bundles": latest,
            "current": current,
            "message": message,
        },
    )
