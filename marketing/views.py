from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import FashionConsultLeadForm
from .models import SocialContentBundle
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

    message = ""
    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "regenerate_hub":
            bundle = regenerate_bundle(
                save=True, bundle_kind=SocialContentBundle.Kind.HUB_SOCIAL
            )
            if bundle.success:
                message = f"Hub digest saved (bundle #{bundle.pk})."
            else:
                message = f"Regeneration failed: {bundle.error[:500]}"
        elif action == "regenerate_instagram_app":
            bundle = regenerate_bundle(
                save=True, bundle_kind=SocialContentBundle.Kind.INSTAGRAM_APP
            )
            if bundle.success:
                message = f"iPhone app Instagram pack saved (bundle #{bundle.pk}). Copy caption + image prompt below."
            else:
                message = f"App promo failed: {bundle.error[:500]}"

    latest = SocialContentBundle.objects.order_by("-created_at")[:20]
    current_hub = (
        SocialContentBundle.objects.filter(bundle_kind=SocialContentBundle.Kind.HUB_SOCIAL)
        .order_by("-created_at")
        .first()
    )
    current_app = (
        SocialContentBundle.objects.filter(bundle_kind=SocialContentBundle.Kind.INSTAGRAM_APP)
        .order_by("-created_at")
        .first()
    )
    return render(
        request,
        "marketing/social_content_dashboard.html",
        {
            "bundles": latest,
            "current_hub": current_hub,
            "current_app": current_app,
            "message": message,
        },
    )
