import base64
import json
import uuid
from decimal import Decimal, InvalidOperation
from datetime import timedelta
from pathlib import Path

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import TemplateView, DetailView, ListView
from django.contrib.auth.views import LoginView, PasswordResetView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import login, authenticate, get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import requires_csrf_token
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.db import transaction
from django.db.models import Q
from django.urls import reverse_lazy, reverse
from .forms import DesignerSignUpForm, DesignerLoginForm, DesignerPasswordResetForm
from .auth_utils import ensure_designer_access
from .models import (
    DesignerProfile,
    SubscriptionPlan,
    UserSubscription,
    Design,
    DesignImage,
    Collection,
    Event,
    WebAuthnCredential,
    DesignerAISession,
    DesignerAIMessage,
    DocPage,
)

from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticationCredential,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    PublicKeyCredentialUserEntity,
    RegistrationCredential,
    UserVerificationRequirement,
)


def _base64url_from_bytes(value: bytes) -> str:
    if not isinstance(value, (bytes, bytearray)):
        raise TypeError("value must be bytes")
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _bytes_from_base64url(data: str) -> bytes:
    if not isinstance(data, str):
        raise TypeError("data must be str")
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _request_wants_json(request) -> bool:
    requested_with = (request.headers.get("x-requested-with") or "").lower()
    if requested_with == "xmlhttprequest":
        return True
    accept_header = request.headers.get("Accept") or ""
    if "application/json" in accept_header:
        return True
    content_type = request.headers.get("Content-Type") or ""
    return content_type.startswith("application/json")


def _strtobool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _save_design_from_request(request, *, design=None):
    """
    Create or update a Design instance based on the incoming request data.
    Returns a tuple of (design_instance, errors_dict).
    """

    user = request.user
    is_create = design is None
    instance = design or Design(designer=user)

    data = request.POST
    files = request.FILES
    errors = {}

    # Core fields
    title = (data.get("title") or "").strip()
    if not title:
        errors["title"] = "Design title is required."

    season = (data.get("season") or "").strip()
    if not season:
        errors["season"] = "Season is required."

    year_raw = (data.get("year") or "").strip()
    year_value = instance.year
    if year_raw:
        try:
            year_value = int(year_raw)
        except ValueError:
            errors["year"] = "Enter a valid year."
    elif is_create:
        errors["year"] = "Year is required."

    slug_input = (data.get("slug") or "").strip()
    if slug_input:
        slug_qs = Design.objects.filter(slug__iexact=slug_input)
        if instance.pk:
            slug_qs = slug_qs.exclude(pk=instance.pk)
        if slug_qs.exists():
            errors["slug"] = "Another design is already using this URL slug."

    cover_image_file = files.get("cover_image")
    if is_create and not (cover_image_file or instance.cover_image):
        errors["cover_image"] = "Please provide a cover image for this design."

    target_price_value = None
    target_price_raw = (data.get("target_price") or "").strip()
    if target_price_raw:
        try:
            target_price_value = Decimal(target_price_raw)
        except InvalidOperation:
            errors["target_price"] = "Enter a valid price (e.g., 199.99)."

    # Tech pack uploads
    pdf_upload = files.get("techpack_pdf")
    excel_upload = files.get("techpack_excel")
    techpack_combo_file = files.get("techpack_file")
    if techpack_combo_file:
        extension = Path(techpack_combo_file.name).suffix.lower()
        if extension == ".pdf":
            pdf_upload = techpack_combo_file
        elif extension in {".xls", ".xlsx"}:
            excel_upload = techpack_combo_file
        else:
            errors["techpack_file"] = "Unsupported tech pack format. Upload PDF or Excel files."

    additional_images = files.getlist("additional_images")

    if errors:
        return instance, errors

    # Assign basic fields
    instance.title = title
    instance.season = season
    instance.year = year_value
    instance.description = (data.get("description") or "").strip()

    # Classification & metadata
    instance.category = (data.get("category") or "").strip()
    instance.target_market = (data.get("target_market") or "").strip()
    instance.featured = _strtobool(data.get("featured")) or _strtobool(data.get("is_featured"))

    instance.fabric_type = (data.get("fabric_type") or "").strip()
    instance.fabric_weight = (data.get("fabric_weight") or "").strip()
    fabric_details_input = (data.get("fabric_details") or "").strip()
    if not fabric_details_input:
        fabric_details_input = ", ".join(
            filter(None, [instance.fabric_type, instance.fabric_weight])
        )
    instance.fabric_details = fabric_details_input

    instance.color_palette = (data.get("color_palette") or "").strip()
    instance.size_range = (data.get("size_range") or "").strip()
    instance.target_price = target_price_value

    technical_notes = (
        data.get("technical_notes")
        or data.get("production_notes")
        or ""
    )
    instance.production_notes = technical_notes.strip()
    instance.design_notes = (data.get("design_notes") or "").strip()

    published_flag = _strtobool(data.get("published")) or _strtobool(data.get("is_public"))
    instance.published = published_flag

    if slug_input:
        instance.slug = slug_input

    if cover_image_file:
        instance.cover_image = cover_image_file

    if pdf_upload:
        instance.techpack_pdf = pdf_upload
    if excel_upload:
        instance.techpack_excel = excel_upload

    # Validate model-level constraints
    try:
        instance.full_clean(exclude=["slug"])
    except ValidationError as exc:
        for field_name, messages_list in exc.message_dict.items():
            if not messages_list:
                continue
            combined_message = " ".join(str(message) for message in messages_list)
            errors[field_name] = combined_message

    if errors:
        return instance, errors

    instance.save()

    # Attach additional gallery images
    if additional_images:
        existing_count = instance.images.count()
        for offset, image_file in enumerate(additional_images, start=1):
            DesignImage.objects.create(
                design=instance,
                image=image_file,
                order=existing_count + offset,
            )

    return instance, {}


def _find_user_by_identifier(identifier: str):
    identifier = (identifier or "").strip()
    if not identifier:
        return None

    UserModel = get_user_model()

    try:
        return UserModel.objects.get(username__iexact=identifier)
    except UserModel.DoesNotExist:
        try:
            return UserModel.objects.get(email__iexact=identifier)
        except UserModel.DoesNotExist:
            return None

def signup_view(request):
    if request.method == "POST":
        # Attempt to restore an existing but inactive account based on username/email
        desired_username = (request.POST.get("username") or "").strip()
        email_input = (request.POST.get("email") or "").strip().lower()
        website_url = (request.POST.get("website_url") or "").strip()
        password1 = request.POST.get("password1") or ""
        password2 = request.POST.get("password2") or ""

        if password1 and password1 == password2:
            inactive_user = (
                User.objects.filter(
                    Q(is_active=False),
                    Q(username__iexact=desired_username) | Q(email__iexact=email_input),
                )
                .order_by("id")
                .first()
            )

            if inactive_user is not None:
                # Validate password strength before restoring
                try:
                    validate_password(password1, user=inactive_user)
                except ValidationError as exc:
                    form = DesignerSignUpForm(request.POST)
                    form.add_error("password1", exc)
                    messages.error(request, "Please correct the errors below.")
                    return render(request, "registration/signup.html", {"form": form})

                # Restore user account
                inactive_user.is_active = True
                if email_input:
                    inactive_user.email = email_input
                inactive_user.set_password(password1)
                inactive_user.save()

                # Ensure related records exist
                ensure_designer_access(inactive_user)
                profile = inactive_user.designer_profile
                # Persist optional website URL if valid
                if website_url:
                    try:
                        URLValidator()(website_url)
                        profile.portfolio_website = website_url
                        profile.save()
                    except ValidationError:
                        # Ignore invalid URL in restore path; do not block restore
                        pass

                # Log the user in using identifier they provided (email or username)
                user_identifier = email_input or desired_username
                user_auth = authenticate(request, username=user_identifier, password=password1)
                if user_auth is not None and user_auth.is_active:
                    login(request, user_auth)
                    return redirect("designer_dashboard")

                messages.success(request, "Account restored. Please log in.")
                return redirect("login")

        # Fall back to normal signup flow
        form = DesignerSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            raw_password = form.cleaned_data.get("password1")
            user_auth = authenticate(request, username=user.username, password=raw_password)
            if user_auth is not None and user_auth.is_active:
                login(request, user_auth)
                return redirect("designer_dashboard")
            messages.success(request, "Account created. Please log in.")
            return redirect("login")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = DesignerSignUpForm()

    return render(request, "registration/signup.html", {"form": form})

# Basic view classes for URL compatibility
class HomePageView(TemplateView):
    template_name = "designer_portfolio/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Provide featured designers for the homepage slideshow.
        # Currently: show the latest active designer profiles (up to 8).
        # If curation is needed later, add a boolean flag on DesignerProfile and filter by it.
        try:
            designers_qs = (
                DesignerProfile.objects.filter(user__is_active=True)
                .select_related("user")
                .order_by("-created_at")
            )
            context["designers"] = list(designers_qs[:8])
        except Exception:
            # Fallback to an empty list if the database or model is unavailable
            context["designers"] = []
        
        # Provide collections for the homepage slideshow
        try:
            collections_qs = Collection.objects.order_by("-year", "name")
            context["collections"] = list(collections_qs)
        except Exception:
            # Fallback to an empty list if the database or model is unavailable
            context["collections"] = []
        
        return context

class AboutView(TemplateView):
    template_name = "designer_portfolio/about.html"

class AboutSiteView(TemplateView):
    template_name = "designer_portfolio/about_site.html"

class CollectionsPageView(TemplateView):
    template_name = "designer_portfolio/collections.html"

class CollectionDetailView(DetailView):
    template_name = "designer_portfolio/collection_detail.html"

class DesignListView(TemplateView):
    template_name = "designer_portfolio/designs.html"

class DesignDetailView(DetailView):
    template_name = "designer_portfolio/design_detail.html"
class EventListView(TemplateView):
    template_name = "designer_portfolio/events.html"
class EventDetailView(DetailView):
    template_name = "designer_portfolio/event_detail.html"
class DesignerDashboardView(LoginRequiredMixin, TemplateView):
    template_name = "designer_portfolio/designer_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Simplified dashboard to avoid potential issues
        try:
            user_designs_qs = Design.objects.filter(designer=user).order_by("-created_at")
            recent_designs = list(user_designs_qs[:8])
            total_designs = user_designs_qs.count()
        except Exception as e:
            # Fallback if there's an issue with Design model
            recent_designs = []
            total_designs = 0

        try:
            total_collections = Collection.objects.count()
        except Exception as e:
            total_collections = 0

        try:
            total_events = Event.objects.count()
        except Exception as e:
            total_events = 0

        try:
            recent_collections = list(Collection.objects.order_by("-year", "name")[:5])
        except Exception as e:
            recent_collections = []

        context.update(
            {
                "current_section": "dashboard",
                "total_designs": total_designs,
                "total_collections": total_collections,
                "total_events": total_events,
                "user_designs": recent_designs,
                "recent_designs": recent_designs,
                "recent_collections": recent_collections,
            }
        )

        return context

class PendingDesignersView(ListView):
    template_name = "designer_portfolio/pending_designers.html"

# ViewSets (minimal)
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny

class BrandViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response([])

class CollectionViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response([])

class DesignViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response([])

class EventViewSet(viewsets.ViewSet):
    def list(self, request):
        return Response([])

# ---- API: Designer Registration ----
class DesignerRegistrationView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        data = getattr(request, "data", {}) or {}
        username = (data.get("username") or "").strip()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        website_url = (data.get("website_url") or data.get("portfolio_website") or "").strip()
        subscription_plan = (data.get("subscription_plan") or "").strip()
        payment_method = (data.get("payment_method") or "").strip()

        # If a previously registered but inactive user exists, restore their account
        if email or username:
            inactive_user = (
                User.objects.filter(
                    Q(is_active=False), Q(username__iexact=username) | Q(email__iexact=email)
                )
                .order_by("id")
                .first()
            )
            if inactive_user is not None:
                errors = {}
                if not password:
                    errors["password"] = "This field is required."
                else:
                    try:
                        validate_password(password, user=inactive_user)
                    except ValidationError as exc:
                        errors["password"] = list(exc.messages)

                if errors:
                    return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

                inactive_user.is_active = True
                if email:
                    inactive_user.email = email
                inactive_user.set_password(password)
                inactive_user.save()

                # Ensure related records
                ensure_designer_access(inactive_user)
                profile = inactive_user.designer_profile
                if website_url:
                    try:
                        URLValidator()(website_url)
                        profile.portfolio_website = website_url
                        profile.save()
                    except ValidationError:
                        pass

                return Response(
                    {"message": "Account restored. You can now sign in."},
                    status=status.HTTP_200_OK,
                )

        errors = {}
        if not username:
            errors["username"] = "This field is required."
        if not email:
            errors["email"] = "This field is required."
        if not password:
            errors["password"] = "This field is required."
        if User.objects.filter(username__iexact=username).exists():
            errors["username"] = "Username is already taken."
        if User.objects.filter(email__iexact=email).exists():
            errors["email"] = "Email is already registered."

        if not errors and password:
            try:
                validate_password(password)
            except ValidationError as exc:
                errors["password"] = list(exc.messages)

        if errors:
            return Response({"errors": errors}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            user = User.objects.create_user(username=username, email=email, password=password)
            # Activate designer accounts immediately
            user.is_active = True
            user.save()

            ensure_designer_access(user)
            profile = user.designer_profile
            if website_url:
                try:
                    URLValidator()(website_url)
                    profile.portfolio_website = website_url
                    profile.save()
                except ValidationError:
                    pass

            plan_instance = None
            if subscription_plan:
                plan_instance = SubscriptionPlan.objects.filter(name=subscription_plan, is_active=True).first()

            trial_days = 30
            trial_end = timezone.now() + timedelta(days=trial_days)

            subscription = user.subscription
            update_fields = set()

            if plan_instance and subscription.plan != plan_instance:
                subscription.plan = plan_instance
                update_fields.add("plan")

            desired_payment_method = payment_method if payment_method else None
            if subscription.payment_method != desired_payment_method:
                subscription.payment_method = desired_payment_method
                update_fields.add("payment_method")

            for field_name in ["trial_end_date", "next_billing_date"]:
                if getattr(subscription, field_name) != trial_end:
                    setattr(subscription, field_name, trial_end)
                    update_fields.add(field_name)

            if subscription.trial_start_date is None:
                subscription.trial_start_date = timezone.now()
                update_fields.add("trial_start_date")

            if subscription.status != "free_trial":
                subscription.status = "free_trial"
                update_fields.add("status")

            if update_fields:
                subscription.save(update_fields=list(update_fields))

            def send_registration_emails():
                # Welcome email to designer
                send_mail(
                    subject="Welcome to designer ? Your Account Is Ready",
                    message=(
                        f"Hello {username},\n\n"
                        "Thanks for registering as a designer with designer.\n"
                        "Your account is now active. You can sign in and access your dashboard immediately.\n\n"
                        "Best,\nTeam designer"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=True,
                )

                # Internal notification email to owner
                owner_email = getattr(settings, "ADMIN_EMAIL", None)
                if owner_email:
                    send_mail(
                        subject="New Designer Registration ? Review Needed",
                        message=(
                            "A new designer has registered and is pending approval.\n\n"
                            f"Username: {username}\n"
                            f"Email: {email}\n"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[owner_email],
                        fail_silently=True,
                    )

            transaction.on_commit(send_registration_emails)

        return Response(
            {"message": "Registration successful. You can now sign in."},
            status=status.HTTP_201_CREATED,
        )


@login_required
@require_POST
def webauthn_register_options(request):
    user = request.user

    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (TypeError, ValueError):
        payload = {}

    nickname = (payload.get("nickname") or "").strip()

    exclude = [
        PublicKeyCredentialDescriptor(id=cred.credential_id)
        for cred in user.webauthn_credentials.all()
    ]

    selection = AuthenticatorSelectionCriteria(
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    options = generate_registration_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        rp_name=settings.WEBAUTHN_RP_NAME,
        user=PublicKeyCredentialUserEntity(
            id=str(user.pk).encode("utf-8"),
            name=user.username,
            display_name=user.get_full_name() or user.username,
        ),
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=selection,
        exclude_credentials=exclude,
    )

    request.session["webauthn_registration_challenge"] = _base64url_from_bytes(options.challenge)
    request.session["webauthn_registration_nickname"] = nickname
    request.session.modified = True

    return JsonResponse(json.loads(options_to_json(options)))


@login_required
@require_POST
def webauthn_register_verify(request):
    expected_challenge = request.session.get("webauthn_registration_challenge")
    if not expected_challenge:
        return JsonResponse({"error": "missing_challenge"}, status=400)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid_payload"}, status=400)

    try:
        credential = RegistrationCredential.parse_raw(json.dumps(payload))
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"error": "invalid_credential", "detail": str(exc)}, status=400)

    try:
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            require_user_verification=True,
            allow_insecure_localhost=settings.WEBAUTHN_ALLOW_INSECURE_LOCALHOST,
        )
    except Exception as exc:  # noqa: BLE001
        request.session.pop("webauthn_registration_challenge", None)
        request.session.pop("webauthn_registration_nickname", None)
        request.session.modified = True
        return JsonResponse({"error": "registration_failed", "detail": str(exc)}, status=400)

    transports = getattr(credential.response, "transports", None) or []
    nickname = request.session.pop("webauthn_registration_nickname", "").strip()

    credential_obj, _ = WebAuthnCredential.objects.update_or_create(
        user=request.user,
        credential_id=verification.credential_id,
        defaults={
            "public_key": verification.credential_public_key,
            "sign_count": verification.sign_count,
            "transports": transports,
            "nickname": nickname,
        },
    )

    request.session.pop("webauthn_registration_challenge", None)
    request.session.modified = True

    return JsonResponse(
        {
            "status": "ok",
            "credential_id": _base64url_from_bytes(verification.credential_id),
            "credential_pk": credential_obj.pk,
        }
    )


@require_POST
def webauthn_authenticate_options(request):
    try:
        payload = json.loads(request.body.decode("utf-8")) if request.body else {}
    except (TypeError, ValueError):
        payload = {}

    identifier = payload.get("username") or payload.get("email")
    user = _find_user_by_identifier(identifier)

    if not user or not user.is_active:
        return JsonResponse({"error": "user_not_found"}, status=404)

    credentials = list(WebAuthnCredential.objects.filter(user=user))
    if not credentials:
        return JsonResponse({"error": "no_passkeys"}, status=400)

    options = generate_authentication_options(
        rp_id=settings.WEBAUTHN_RP_ID,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=cred.credential_id)
            for cred in credentials
        ],
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    request.session["webauthn_authentication_challenge"] = _base64url_from_bytes(options.challenge)
    request.session["webauthn_authentication_user_id"] = user.pk
    request.session.modified = True

    return JsonResponse(json.loads(options_to_json(options)))


@require_POST
def webauthn_authenticate_verify(request):
    expected_challenge = request.session.get("webauthn_authentication_challenge")
    user_id = request.session.get("webauthn_authentication_user_id")

    if not expected_challenge or not user_id:
        return JsonResponse({"error": "missing_challenge"}, status=400)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (TypeError, ValueError):
        return JsonResponse({"error": "invalid_payload"}, status=400)

    remember_me = bool(payload.get("remember_me"))
    next_url = payload.get("next") or ""

    try:
        credential = AuthenticationCredential.parse_raw(json.dumps(payload))
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"error": "invalid_credential", "detail": str(exc)}, status=400)

    UserModel = get_user_model()
    try:
        user = UserModel.objects.get(pk=user_id, is_active=True)
    except UserModel.DoesNotExist:
        request.session.pop("webauthn_authentication_challenge", None)
        request.session.pop("webauthn_authentication_user_id", None)
        request.session.modified = True
        return JsonResponse({"error": "user_not_found"}, status=404)

    raw_id = payload.get("rawId")
    if not raw_id:
        return JsonResponse({"error": "missing_credential_id"}, status=400)

    credential_id = _bytes_from_base64url(raw_id)

    try:
        stored_credential = WebAuthnCredential.objects.get(user=user, credential_id=credential_id)
    except WebAuthnCredential.DoesNotExist:
        return JsonResponse({"error": "credential_not_found"}, status=404)

    try:
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=settings.WEBAUTHN_RP_ID,
            expected_origin=settings.WEBAUTHN_ORIGIN,
            credential_public_key=stored_credential.public_key,
            credential_current_sign_count=stored_credential.sign_count,
            require_user_verification=True,
            allow_insecure_localhost=settings.WEBAUTHN_ALLOW_INSECURE_LOCALHOST,
        )
    except Exception as exc:  # noqa: BLE001
        return JsonResponse({"error": "authentication_failed", "detail": str(exc)}, status=400)

    stored_credential.sign_count = verification.new_sign_count
    stored_credential.last_used_at = timezone.now()
    stored_credential.save(update_fields=["sign_count", "last_used_at", "updated_at"])

    request.session.pop("webauthn_authentication_challenge", None)
    request.session.pop("webauthn_authentication_user_id", None)
    request.session.modified = True

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")

    if remember_me:
        session_age_seconds = getattr(settings, "REMEMBER_ME_SESSION_AGE", 60 * 60 * 24 * 30)
        request.session.set_expiry(session_age_seconds)
    else:
        request.session.set_expiry(0)

    redirect_to = settings.LOGIN_REDIRECT_URL
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        redirect_to = next_url

    return JsonResponse({"status": "ok", "redirect_url": redirect_to})


@login_required
@require_POST
def webauthn_delete_credential(request, credential_id):
    try:
        credential = request.user.webauthn_credentials.get(pk=credential_id)
    except WebAuthnCredential.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)

    credential.delete()
    return JsonResponse({"status": "ok"})
# Placeholder functions
def upload_design(request):
    if request.user.is_authenticated:
        return redirect("designer_design_create")
    return redirect("login")


def approve_designer(request, user_id):
    return JsonResponse({"status": "ok"})


def reject_designer(request, user_id):
    return JsonResponse({"status": "ok"})


def reinstate_designer(request, designer_id):
    return JsonResponse({"status": "ok"})


@login_required
def designer_design_edit_view(request, design_id):
    design = get_object_or_404(Design, pk=design_id, designer=request.user)

    if request.method == "POST":
        updated_design, errors = _save_design_from_request(request, design=design)
        if errors:
            if _request_wants_json(request):
                return JsonResponse({"success": False, "errors": errors}, status=400)

            messages.error(request, "Please correct the highlighted errors.")
            context = {
                "current_section": "designs",
                "design": updated_design,
                "form_errors": errors,
                "gallery_images": updated_design.images.order_by("order", "created_at"),
            }
            return render(
                request,
                "designer_portfolio/designer_design_edit.html",
                context,
                status=400,
            )

        state_message = "Design updated and published." if updated_design.published else "Design updated as draft."
        messages.success(request, state_message)
        if _request_wants_json(request):
            return JsonResponse(
                {
                    "success": True,
                    "design_id": updated_design.pk,
                    "redirect_url": reverse("designer_designs"),
                }
            )
        return redirect("designer_designs")

    context = {
        "current_section": "designs",
        "design": design,
        "form_errors": {},
        "gallery_images": design.images.order_by("order", "created_at"),
    }
    return render(request, "designer_portfolio/designer_design_edit.html", context)


@login_required
@require_POST
def designer_design_delete_view(request, design_id):
    design = get_object_or_404(Design, pk=design_id, designer=request.user)
    design.delete()

    messages.success(request, "Design deleted successfully.")
    if _request_wants_json(request):
        return JsonResponse(
            {
                "success": True,
                "redirect_url": reverse("designer_designs"),
            }
        )
    return redirect("designer_designs")


@login_required
def designer_design_detail_api(request, design_id):
    design = get_object_or_404(Design, pk=design_id, designer=request.user)

    data = {
        "id": design.pk,
        "title": design.title,
        "slug": design.slug,
        "season": design.season,
        "year": design.year,
        "description": design.description,
        "published": design.published,
        "category": design.category,
        "target_market": design.target_market,
        "featured": design.featured,
        "fabric_type": design.fabric_type,
        "fabric_weight": design.fabric_weight,
        "fabric_details": design.fabric_details,
        "color_palette": design.color_palette,
        "size_range": design.size_range,
        "target_price": str(design.target_price) if design.target_price is not None else "",
        "production_notes": design.production_notes,
        "design_notes": design.design_notes,
        "has_techpack": design.has_techpack,
        "techpack_pdf": design.techpack_pdf.url if design.techpack_pdf else "",
        "techpack_excel": design.techpack_excel.url if design.techpack_excel else "",
        "cover_image": design.cover_image.url if design.cover_image else "",
        "created_at": design.created_at.isoformat() if design.created_at else "",
        "updated_at": design.updated_at.isoformat() if design.updated_at else "",
        "detail_url": reverse("design_detail", args=[design.slug]) if design.slug else "",
    }
    data["images"] = [
        {
            "id": image.pk,
            "url": image.image.url,
            "order": image.order,
            "caption": image.caption,
        }
        for image in design.images.order_by("order", "created_at")
    ]

    return JsonResponse({"success": True, "design": data})

def subscription_dashboard(request):
    return render(request, "designer_portfolio/subscription_dashboard.html", {})

def change_subscription_plan(request):
    return JsonResponse({"status": "ok"})

def cancel_subscription(request):
    return JsonResponse({"status": "ok"})

def payment_methods(request):
    return render(request, "designer_portfolio/payment_methods.html", {})

def billing_history(request):
    return render(request, "designer_portfolio/billing_history.html", {})

def create_stripe_setup_intent(request):
    return JsonResponse({"status": "ok"})

def stripe_webhook(request):
    return JsonResponse({"status": "ok"})

def create_paypal_subscription(request):
    return JsonResponse({"status": "ok"})

def paypal_webhook(request):
    return JsonResponse({"status": "ok"})

def generate_techpack(request, slug):
    return JsonResponse({"status": "ok"})

@login_required
def dashboard_view(request):
    return render(request, "designer_portfolio/dashboard.html", {"current_section": "dashboard"})

@login_required
def designer_designs_view(request):
    # Ensure related records exist
    DesignerProfile.objects.get_or_create(user=request.user)
    if not hasattr(request.user, "subscription"):
        trial_end = timezone.now() + timedelta(days=30)
        UserSubscription.objects.create(
            user=request.user,
            plan=None,
            status="free_trial",
            payment_method=None,
            trial_end_date=trial_end,
            next_billing_date=trial_end,
        )

    designs = Design.objects.filter(designer=request.user).order_by("-created_at")
    available_years = (
        designs.values_list("year", flat=True).distinct().order_by("-year")
    )

    return render(
        request,
        "designer_portfolio/designer_designs.html",
        {
            "current_section": "designs",
            "designs": designs,
            "available_years": available_years,
        },
    )

@login_required
def designer_design_create_view(request):
    # Ensure related records exist
    DesignerProfile.objects.get_or_create(user=request.user)
    if not hasattr(request.user, "subscription"):
        trial_end = timezone.now() + timedelta(days=30)
        UserSubscription.objects.create(
            user=request.user,
            plan=None,
            status="free_trial",
            payment_method=None,
            trial_end_date=trial_end,
            next_billing_date=trial_end,
        )

    context = {
        "current_section": "designs",
        "current_year": timezone.now().year,
        "form_errors": {},
        "form_values": {},
    }

    if request.method == "POST":
        design, errors = _save_design_from_request(request)
        if errors:
            if _request_wants_json(request):
                return JsonResponse({"success": False, "errors": errors}, status=400)

            messages.error(request, "Please correct the highlighted errors.")
            context["form_errors"] = errors
            context["form_values"] = {key: value for key, value in request.POST.items()}
            return render(
                request,
                "designer_portfolio/designer_design_create.html",
                context,
                status=400,
            )

        success_message = (
            "Design uploaded and published." if design.published else "Design saved as draft."
        )
        messages.success(request, success_message)

        if _request_wants_json(request):
            return JsonResponse(
                {
                    "success": True,
                    "design_id": design.pk,
                    "redirect_url": reverse("designer_designs"),
                }
            )

        return redirect("designer_designs")

    return render(request, "designer_portfolio/designer_design_create.html", context)

@login_required
def designer_about_me_view(request):
    user = request.user
    profile, _ = DesignerProfile.objects.get_or_create(user=user)

    # Ensure a subscription record exists (for templates using it)
    if not hasattr(user, "subscription"):
        trial_end = timezone.now() + timedelta(days=30)
        UserSubscription.objects.create(
            user=user,
            plan=None,
            status="free_trial",
            payment_method=None,
            trial_end_date=trial_end,
            next_billing_date=trial_end,
        )

    passkeys = list(user.webauthn_credentials.order_by("created_at"))

    if request.method == "POST":
        # Update basic user fields
        first_name = (request.POST.get("first_name") or user.first_name).strip()
        last_name = (request.POST.get("last_name") or user.last_name).strip()
        email = (request.POST.get("email") or user.email).strip()

        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.save()

        # Update profile fields (map template inputs to model fields)
        profile.bio = request.POST.get("bio", profile.bio)
        profile.location = request.POST.get("location", profile.location)
        profile.education = request.POST.get("education", profile.education)
        # years_of_experience may be empty; coerce safely
        years_val = request.POST.get("years_of_experience", "").strip()
        try:
            profile.years_of_experience = int(years_val) if years_val != "" else profile.years_of_experience
        except ValueError:
            # leave unchanged on bad input
            pass

        # Social/portfolio links
        profile.portfolio_website = request.POST.get("portfolio_website", request.POST.get("website", profile.portfolio_website))
        profile.instagram_handle = request.POST.get("instagram_handle", request.POST.get("instagram", profile.instagram_handle))
        profile.linkedin_profile = request.POST.get("linkedin_profile", request.POST.get("linkedin", profile.linkedin_profile))
        profile.specialization = request.POST.get("specialization", request.POST.get("specializations", profile.specialization))
        profile.contact_email = request.POST.get("contact_email", profile.contact_email)

        # Collaboration preference (support old and corrected field names)
        available_flag = request.POST.get("available_for_collaborations") or request.POST.get("available_for_collaboration")
        profile.available_for_collaborations = bool(available_flag)

        # Handle profile image upload
        if "profile_image" in request.FILES:
            profile.profile_image = request.FILES["profile_image"]

        profile.save()

        messages.success(request, "Your profile was updated successfully.")
        return redirect("designer_about_me")

    # Stats for header widgets
    try:
        total_designs = Design.objects.filter(designer=user).count()
    except Exception:
        total_designs = 0

    return render(
        request,
        "designer_portfolio/designer_about_me.html",
        {
            "current_section": "about",
            "designer_profile": profile,
            "total_designs": total_designs,
            "passkeys": passkeys,
        },
    )

@login_required
def designer_contact_view(request):
    profile, _ = DesignerProfile.objects.get_or_create(user=request.user)
    if not hasattr(request.user, "subscription"):
        trial_end = timezone.now() + timedelta(days=30)
        UserSubscription.objects.create(
            user=request.user,
            plan=None,
            status="free_trial",
            payment_method=None,
            trial_end_date=trial_end,
            next_billing_date=trial_end,
        )

    # Count non-empty social links for small stat
    social_links_count = sum(
        1
        for value in [
            getattr(profile, "portfolio_website", ""),
            getattr(profile, "instagram_handle", ""),
            getattr(profile, "linkedin_profile", ""),
        ]
        if value
    )

    return render(
        request,
        "designer_portfolio/designer_contact.html",
        {
            "current_section": "contact",
            "designer_profile": profile,
            "social_links_count": social_links_count,
        },
    )

from django.contrib.auth import logout
def logout_view(request):
    logout(request)
    return redirect('home')

class DesignersListView(ListView):
    model = DesignerProfile
    template_name = "designer_portfolio/designers.html"
    context_object_name = "designers"
    paginate_by = 20

    def get_queryset(self):
        # Only return profiles for active users
        return DesignerProfile.objects.filter(
            user__is_active=True
        ).select_related('user').order_by('-created_at')


class DesignerLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = DesignerLoginForm

    def form_valid(self, form):
        response = super().form_valid(form)
        remember_me = form.cleaned_data.get("remember_me")

        # Control session expiry based on remember_me
        # When remember_me is True, use a longer session age; otherwise expire at browser close
        if remember_me:
            # Use custom setting if provided; fallback to 30 days
            session_age_seconds = getattr(settings, "REMEMBER_ME_SESSION_AGE", 60 * 60 * 24 * 30)
            self.request.session.set_expiry(session_age_seconds)
        else:
            # 0 = expire at browser close
            self.request.session.set_expiry(0)

        return response


class DesignerPasswordResetView(PasswordResetView):
    form_class = DesignerPasswordResetForm
    template_name = "registration/password_reset_form.html"
    email_template_name = "registration/password_reset_email.html"
    subject_template_name = "registration/password_reset_subject.txt"
    success_url = reverse_lazy("password_reset_done")


# --- Security/Errors ---
@requires_csrf_token
def csrf_failure(request, reason=""):
    """Custom handler for CSRF failures.

    Returns JSON for AJAX/JSON requests and a friendly HTML page otherwise.
    """
    accepts_header = (request.headers.get("Accept") or "").lower()
    is_ajax = (request.headers.get("x-requested-with") or "").lower() == "xmlhttprequest"
    wants_json = "application/json" in accepts_header

    if is_ajax or wants_json:
        payload = {
            "error": "csrf_failed",
            "message": "Your session expired or the form is stale. Please refresh the page and try again.",
        }
        if settings.DEBUG:
            payload["reason"] = reason or ""
        return JsonResponse(payload, status=403)

    context = {
        "reason": reason or "",
        "debug": settings.DEBUG,
    }
    return render(request, "errors/403_csrf.html", context=context, status=403)


# ==================== Designer AI Chat ====================

def _get_designer_ai_system_prompt() -> str:
    """Returns the system prompt for Designer AI."""
    return """You are "GlobalDesignerHub Designer AI", an assistant for designers using GlobalDesignerHub (GDH).

Your scope:
- Answer questions about design portfolios (fashion, graphic, UX/UI, interior, illustration, etc.).
- Help with portfolio structure, case studies, project descriptions, and image/video presentation.
- Help users understand and use GlobalDesignerHub features: creating profiles, uploading designs, collections, collaboration, privacy, and sharing.
- Help with light website issues related to GDH (image sizes, formats, performance tips), but do NOT give server admin or low-level dev instructions unless clearly asked by a developer.
- Always prefer solutions that use GDH features (collections, tags, categories, collaboration tools).

When a question is NOT about design, portfolios, or GDH, politely say you are focused only on designer + GlobalDesignerHub topics and redirect them.

Whenever relevant:
- Link to the correct GDH documentation page using format: (/docs/designers/getting-started) or (/docs/api/overview)
- If the question is about integrations, show the relevant API or integration docs links.

Tone: friendly, professional, and supportive of creative people. Avoid strong opinions; give options and best practices."""


def _get_designer_ai_responses() -> dict:
    """Returns a dictionary of common responses for fallback when AI is not available."""
    return {
        "portfolio": {
            "keywords": ["portfolio", "structure", "layout", "case study", "project"],
            "response": """Great question about portfolios! Here are some best practices:

**Portfolio Structure:**
- Start with your strongest work
- Group projects by category or collection
- Include 3-5 high-quality images per project
- Add brief descriptions explaining your process

**On GlobalDesignerHub:**
- Use Collections to group related projects
- Add descriptive captions to each image
- Tag your work by category for easy discovery

For more details, check out: (/docs/designers/portfolio-layouts)"""
        },
        "upload": {
            "keywords": ["upload", "image", "size", "format", "video"],
            "response": """Here's how to handle media on GlobalDesignerHub:

**Image Guidelines:**
- Recommended size: 1920x1080px or larger
- Formats: JPG, PNG, WebP
- Max file size: 10MB per image
- For best quality, use high-resolution images

**Video Guidelines:**
- Formats: MP4, WebM
- Max file size: 100MB
- Recommended resolution: 1080p

**Upload Process:**
1. Go to Dashboard → Designs
2. Click "New Design"
3. Upload your images/videos
4. Add titles, descriptions, and tags

Need more help? See: (/docs/designers/media-guidelines)"""
        },
        "profile": {
            "keywords": ["profile", "create", "setup", "account"],
            "response": """Setting up your GlobalDesignerHub profile is easy:

**Getting Started:**
1. Sign up for an account
2. Complete your designer profile
3. Add a profile image and bio
4. Start uploading your work

**Profile Tips:**
- Use a professional photo
- Write a compelling bio highlighting your expertise
- Add your location and specialization
- Link your social media accounts

Learn more: (/docs/designers/getting-started)"""
        },
        "api": {
            "keywords": ["api", "integration", "embed", "sync", "webhook"],
            "response": """GlobalDesignerHub offers a REST API for integrations:

**API Features:**
- Portfolio management (list, create, update projects)
- Media uploads
- Collection management
- Authentication via API keys

**Getting Started:**
- API Overview: (/docs/api/overview)
- Authentication: (/docs/api/auth)
- Portfolio API: (/docs/api/portfolios)

**Embedding:**
You can embed your GDH portfolio on your own website using our embed widgets.

For developers: (/docs/api/overview)"""
        },
        "default": {
            "response": """I'm here to help with design portfolios and GlobalDesignerHub!

I can assist with:
- Portfolio structure and layouts
- Uploading and organizing your work
- Using GDH features
- API and integration questions

Try asking:
- "How do I create my portfolio?"
- "What image size should I upload?"
- "How do I use the API?"

Or check out our docs: (/docs/designers/getting-started)"""
        }
    }


def _get_ai_response_fallback(message: str, context_page: str = "") -> str:
    """Fallback response when AI service is not available."""
    message_lower = message.lower()
    responses = _get_designer_ai_responses()
    
    # Check for matching keywords
    for key, data in responses.items():
        if key == "default":
            continue
        for keyword in data["keywords"]:
            if keyword in message_lower:
                return data["response"]
    
    return responses["default"]["response"]


@require_POST
@requires_csrf_token
def designer_ai_chat(request):
    """
    API endpoint for Designer AI chat with RAG, session management, and error handling.
    Accepts POST requests with JSON body:
    {
        "message": "user message",
        "context_page": "/dashboard/designs/",
        "current_url": "https://...",
        "language": "en"
    }
    """
    try:
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()
        context_page = data.get("context_page", "")
        current_url = data.get("current_url", "")
        language = data.get("language", "en")
        
        if not user_message:
            return JsonResponse({
                "success": False,
                "error": "Message is required"
            }, status=400)
        
        # Get or create session
        session_id = request.COOKIES.get("designer_ai_session")
        if session_id:
            try:
                session = DesignerAISession.objects.get(session_id=session_id)
            except DesignerAISession.DoesNotExist:
                session = None
        else:
            session = None
        
        if not session:
            session = DesignerAISession.objects.create(
                user=request.user if request.user.is_authenticated else None,
                session_id=str(uuid.uuid4()),
                language=language
            )
        
        # Save user message
        DesignerAIMessage.objects.create(
            session=session,
            role="user",
            content=user_message,
        )
        
        # Build system prompt
        system_prompt = _get_designer_ai_system_prompt()
        
        # Add context about current page
        if context_page:
            context_info = f"\n\nUser is currently on page: {context_page}"
            if "dashboard" in context_page:
                context_info += "\nThey are in the dashboard area."
            if "design" in context_page:
                context_info += "\nThey are working with designs."
            if "collection" in context_page:
                context_info += "\nThey are working with collections."
            system_prompt += context_info
        
        # RAG: Retrieve relevant documentation
        rag_docs = []
        try:
            rag_docs = list(DocPage.objects.filter(
                published=True,
                language=language
            ).filter(
                Q(content__icontains=user_message) |
                Q(title__icontains=user_message) |
                Q(tags__icontains=user_message)
            )[:3])
        except Exception as e:
            if settings.DEBUG:
                print(f"RAG error: {e}")
        
        # Build messages with history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add RAG context if found
        if rag_docs:
            rag_context = "\n\n--- Documentation Context ---\n\n"
            rag_context += "\n\n---\n\n".join(
                f"Title: {doc.title}\nContent: {doc.content[:500]}...\nLink: /docs/{doc.category}/{doc.slug}/"
                for doc in rag_docs
            )
            messages.append({"role": "system", "content": rag_context})
        
        # Add conversation history (last 10 messages)
        history = DesignerAIMessage.objects.filter(session=session).exclude(role="system").order_by("created_at")[:10]
        for msg in history:
            if msg.role in ["user", "assistant"]:
                messages.append({"role": msg.role, "content": msg.content})
        
        # Add current user message
        messages.append({"role": "user", "content": user_message})
        
        # Check if OpenAI is configured
        openai_api_key = os.getenv("OPENAI_API_KEY")
        use_openai = openai_api_key and openai_api_key.strip()
        
        ai_response = None
        
        if use_openai:
            try:
                import openai
                # Support both old and new OpenAI SDK
                try:
                    # New SDK (v1.0+)
                    client = openai.OpenAI(api_key=openai_api_key)
                    response = client.chat.completions.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1000
                    )
                    ai_response = response.choices[0].message.content
                except AttributeError:
                    # Old SDK fallback
                    openai.api_key = openai_api_key
                    response = openai.ChatCompletion.create(
                        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
                        messages=messages,
                        temperature=0.7,
                        max_tokens=1000
                    )
                    ai_response = response.choices[0].message["content"]
                
            except ImportError:
                if settings.DEBUG:
                    print("OpenAI library not installed")
            except Exception as e:
                if settings.DEBUG:
                    print(f"OpenAI error: {e}")
        
        # Fallback to rule-based responses if OpenAI failed
        if not ai_response:
            ai_response = _get_ai_response_fallback(user_message, context_page)
        
        # Save assistant response
        DesignerAIMessage.objects.create(
            session=session,
            role="assistant",
            content=ai_response,
            metadata={"rag_sources": [doc.slug for doc in rag_docs] if rag_docs else []}
        )
        
        # Return response
        response = JsonResponse({
            "success": True,
            "response": ai_response,
            "session_id": str(session.session_id)
        })
        response.set_cookie("designer_ai_session", str(session.session_id), max_age=60*60*24*30)  # 30 days
        return response
        
    except json.JSONDecodeError:
        return JsonResponse({
            "success": False,
            "error": "Invalid JSON"
        }, status=400)
    except Exception as e:
        if settings.DEBUG:
            import traceback
            print(f"🔥 AI ERROR: {e}")
            print(traceback.format_exc())
            return JsonResponse({
                "success": False,
                "error": str(e)
            }, status=500)
        return JsonResponse({
            "success": False,
            "error": "An error occurred. Please try again."
        }, status=500)


def my_conversations(request):
    """View for displaying user's AI chat history."""
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect("login")
    
    sessions = DesignerAISession.objects.filter(user=request.user).order_by("-created_at")[:50]
    
    return render(request, "designer_portfolio/my_conversations.html", {
        "sessions": sessions
    })
