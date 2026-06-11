from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from .forms import (
    BrandPartnershipLeadForm,
    EmergingTalentSubmissionForm,
    EventRegistrationForm,
    FashionConsultLeadForm,
    ForumInterestForm,
    MentorshipApplicationForm,
)
from .models import (
    EmergingTalentFeature,
    Event,
    MentorshipApplication,
    SocialContentBundle,
)
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


# ---------------------------------------------------------------------------
# Events: webinars / workshops / virtual meetups / design jams
# ---------------------------------------------------------------------------

_PUBLIC_EVENT_STATUSES = (
    Event.Status.SCHEDULED,
    Event.Status.LIVE,
    Event.Status.ENDED,
)


def events_list(request):
    """Public list of events: upcoming first, then recent past."""
    now = timezone.now()
    upcoming = (
        Event.objects.filter(
            status__in=(Event.Status.SCHEDULED, Event.Status.LIVE),
            starts_at__gte=now,
        )
        .order_by("starts_at")
    )
    past = (
        Event.objects.filter(status=Event.Status.ENDED)
        .order_by("-starts_at")[:10]
    )
    return render(
        request,
        "marketing/events_list.html",
        {"upcoming": upcoming, "past": past},
    )


@require_http_methods(["GET", "POST"])
def event_detail(request, slug: str):
    event = get_object_or_404(
        Event,
        slug=slug,
        status__in=_PUBLIC_EVENT_STATUSES,
    )

    form = EventRegistrationForm()
    registration = None

    if request.method == "POST":
        if not event.registrations_open:
            form = EventRegistrationForm(request.POST)
            form.add_error(
                None,
                "Registration is closed for this event."
                if event.is_full
                else "This event is no longer open for registration.",
            )
        else:
            form = EventRegistrationForm(request.POST)
            if form.is_valid():
                registration = form.save(event=event)
                return redirect("marketing:event_registered", slug=event.slug)

    return render(
        request,
        "marketing/event_detail.html",
        {
            "event": event,
            "form": form,
            "registration": registration,
        },
    )


def event_registered(request, slug: str):
    event = get_object_or_404(
        Event,
        slug=slug,
        status__in=_PUBLIC_EVENT_STATUSES,
    )
    return render(
        request,
        "marketing/event_registered.html",
        {"event": event},
    )


# ---------------------------------------------------------------------------
# Emerging Talent showcase
# ---------------------------------------------------------------------------


def emerging_talent_list(request):
    features = EmergingTalentFeature.objects.filter(is_published=True)
    return render(
        request,
        "marketing/emerging_talent_list.html",
        {"features": features},
    )


def emerging_talent_detail(request, slug: str):
    feature = get_object_or_404(
        EmergingTalentFeature, slug=slug, is_published=True
    )
    return render(
        request,
        "marketing/emerging_talent_detail.html",
        {"feature": feature},
    )


@require_http_methods(["GET", "POST"])
def emerging_talent_submit(request):
    """Designer self-nomination for the Emerging Talent section."""
    initial = {}
    if request.user.is_authenticated:
        initial = {
            "full_name": (request.user.get_full_name() or "").strip(),
            "email": (request.user.email or "").strip(),
        }

    if request.method == "POST":
        form = EmergingTalentSubmissionForm(request.POST)
        if form.is_valid():
            submission = form.save(commit=False)
            if request.user.is_authenticated:
                submission.user = request.user
            submission.save()
            return redirect("marketing:emerging_talent_submitted")
    else:
        form = EmergingTalentSubmissionForm(initial=initial)

    return render(
        request,
        "marketing/emerging_talent_submit.html",
        {"form": form},
    )


def emerging_talent_submitted(request):
    return render(request, "marketing/emerging_talent_submitted.html")


# ---------------------------------------------------------------------------
# /grads/ — landing page for final-year fashion grad students
# ---------------------------------------------------------------------------


def grads_landing(request):
    """
    Marketing landing page targeting final-year fashion grad students.

    Mirrors the email's three-section structure (Showcase / Stay Ahead /
    Connect) and pulls live content from the rest of the marketing app:
    upcoming events, recent Emerging Talent features.
    """
    now = timezone.now()
    upcoming_events = (
        Event.objects.filter(
            status__in=(Event.Status.SCHEDULED, Event.Status.LIVE),
            starts_at__gte=now,
        )
        .order_by("starts_at")[:3]
    )
    featured_designers = (
        EmergingTalentFeature.objects.filter(is_published=True)[:3]
    )
    return render(
        request,
        "marketing/grads_landing.html",
        {
            "upcoming_events": upcoming_events,
            "featured_designers": featured_designers,
        },
    )


# ---------------------------------------------------------------------------
# Brand partnership lead capture
# ---------------------------------------------------------------------------


@require_http_methods(["GET", "POST"])
def brand_partner(request):
    if request.method == "POST":
        form = BrandPartnershipLeadForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("marketing:brand_partner_thanks")
    else:
        form = BrandPartnershipLeadForm()
    return render(request, "marketing/brand_partner.html", {"form": form})


def brand_partner_thanks(request):
    return render(request, "marketing/brand_partner_thanks.html")


# ---------------------------------------------------------------------------
# Mentorship program
# ---------------------------------------------------------------------------


def mentorship_landing(request):
    return render(request, "marketing/mentorship_landing.html")


_MENTORSHIP_ROLE_BY_PATH = {
    "become-a-mentor": MentorshipApplication.Role.MENTOR,
    "find-a-mentor": MentorshipApplication.Role.MENTEE,
}


@require_http_methods(["GET", "POST"])
def mentorship_apply(request, role_path: str):
    role = _MENTORSHIP_ROLE_BY_PATH.get(role_path)
    if role is None:
        raise Http404("Unknown mentorship role.")

    initial = {}
    if request.user.is_authenticated:
        initial = {
            "full_name": (request.user.get_full_name() or "").strip(),
            "email": (request.user.email or "").strip(),
        }

    if request.method == "POST":
        form = MentorshipApplicationForm(request.POST, role=role)
        if form.is_valid():
            application = form.save(commit=False)
            if request.user.is_authenticated:
                application.user = request.user
            application.save()
            return redirect("marketing:mentorship_applied", role_path=role_path)
    else:
        form = MentorshipApplicationForm(initial=initial, role=role)

    return render(
        request,
        "marketing/mentorship_apply.html",
        {
            "form": form,
            "role": role,
            "role_path": role_path,
            "is_mentor": role == MentorshipApplication.Role.MENTOR,
        },
    )


def mentorship_applied(request, role_path: str):
    if role_path not in _MENTORSHIP_ROLE_BY_PATH:
        raise Http404("Unknown mentorship role.")
    role = _MENTORSHIP_ROLE_BY_PATH[role_path]
    return render(
        request,
        "marketing/mentorship_applied.html",
        {
            "role": role,
            "is_mentor": role == MentorshipApplication.Role.MENTOR,
        },
    )


# ---------------------------------------------------------------------------
# Community forums (placeholder + interest capture)
# ---------------------------------------------------------------------------


@require_http_methods(["GET", "POST"])
def community_forum(request):
    submitted = False
    if request.method == "POST":
        form = ForumInterestForm(request.POST)
        if form.is_valid():
            form.save()
            submitted = True
            form = ForumInterestForm()
    else:
        form = ForumInterestForm()
    return render(
        request,
        "marketing/community_forum.html",
        {"form": form, "submitted": submitted},
    )


# ---------------------------------------------------------------------------
# Staff dashboard for the community feature pack
# ---------------------------------------------------------------------------


@login_required
def community_dashboard(request):
    if not request.user.is_active or not request.user.is_staff:
        raise PermissionDenied()

    now = timezone.now()
    event_counts = Event.objects.aggregate(
        upcoming=Count(
            "id",
            filter=Q(
                status__in=(Event.Status.SCHEDULED, Event.Status.LIVE),
                starts_at__gte=now,
            ),
        ),
        past=Count("id", filter=Q(status=Event.Status.ENDED)),
        drafts=Count("id", filter=Q(status=Event.Status.DRAFT)),
    )
    mentorship_counts = MentorshipApplication.objects.aggregate(
        mentors_active=Count(
            "id",
            filter=Q(
                role=MentorshipApplication.Role.MENTOR,
                status__in=(
                    MentorshipApplication.Status.PENDING,
                    MentorshipApplication.Status.ACTIVE,
                ),
            ),
        ),
        mentees_active=Count(
            "id",
            filter=Q(
                role=MentorshipApplication.Role.MENTEE,
                status__in=(
                    MentorshipApplication.Status.PENDING,
                    MentorshipApplication.Status.ACTIVE,
                ),
            ),
        ),
        matched=Count(
            "id", filter=Q(status=MentorshipApplication.Status.MATCHED)
        ),
    )
    return render(
        request,
        "marketing/community_dashboard.html",
        {
            "event_counts": event_counts,
            "mentorship_counts": mentorship_counts,
            "recent_events": Event.objects.order_by("-created_at")[:10],
            "recent_features": EmergingTalentFeature.objects.order_by("-created_at")[:10],
            "recent_mentor_applications": (
                MentorshipApplication.objects.order_by("-created_at")[:10]
            ),
        },
    )


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
