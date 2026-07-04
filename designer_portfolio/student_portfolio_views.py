import json
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Max, Prefetch
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

from .forms import (
    StudentPortfolioForm,
    StudentPortfolioProjectForm,
    StudentProjectFeedbackForm,
)
from .models import (
    StudentPortfolio,
    StudentPortfolioPlan,
    StudentPortfolioProject,
    StudentPortfolioProjectImage,
    StudentPortfolioSubscription,
    StudentProjectBookmark,
    StudentProjectFeedback,
    StudentProjectLike,
)
from .student_portfolio_templates import SAMPLE_TEMPLATES


def _get_or_create_portfolio(user) -> StudentPortfolio:
    portfolio, _ = StudentPortfolio.objects.get_or_create(user=user)
    return portfolio


def _resolve_next_url(request, fallback: str) -> str:
    candidate = (
        request.POST.get("next")
        or request.GET.get("next")
        or request.META.get("HTTP_REFERER")
        or ""
    ).strip()
    if candidate and url_has_allowed_host_and_scheme(
        candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    if candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return fallback


@login_required
def student_portfolio_dashboard(request):
    portfolio = _get_or_create_portfolio(request.user)
    portfolio_form = StudentPortfolioForm(instance=portfolio)
    project_form = StudentPortfolioProjectForm()

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        if action == "update_portfolio":
            portfolio_form = StudentPortfolioForm(
                request.POST,
                request.FILES,
                instance=portfolio,
            )
            if portfolio_form.is_valid():
                portfolio_form.save()
                messages.success(request, "Student portfolio profile updated.")
                return redirect("student_portfolio_dashboard")
            messages.error(request, "Please fix the profile form errors and try again.")

        elif action == "create_project":
            project_form = StudentPortfolioProjectForm(request.POST, request.FILES)
            if project_form.is_valid():
                project = project_form.save(commit=False)
                project.portfolio = portfolio
                max_order = portfolio.projects.aggregate(max_order=Max("display_order")).get(
                    "max_order"
                )
                project.display_order = (max_order if max_order is not None else -1) + 1
                project.save()
                for i, img_file in enumerate(request.FILES.getlist("gallery_images") or []):
                    StudentPortfolioProjectImage.objects.create(
                        project=project,
                        image=img_file,
                        display_order=i,
                    )
                messages.success(request, "Project added to your portfolio.")
                return redirect("student_portfolio_dashboard")
            messages.error(request, "Please fix the project form errors and try again.")

        elif action == "apply_template":
            template_id = (request.POST.get("template_id") or "").strip()
            template = next((t for t in SAMPLE_TEMPLATES if t["id"] == template_id), None)
            if template:
                max_order = portfolio.projects.aggregate(max_order=Max("display_order")).get(
                    "max_order"
                ) or -1
                for i, sp in enumerate(template.get("suggested_projects", [])):
                    max_order += 1
                    cat = sp.get("category", "other")
                    if cat not in dict(StudentPortfolioProject.Category.choices):
                        cat = "other"
                    StudentPortfolioProject.objects.create(
                        portfolio=portfolio,
                        title=sp.get("title", "Untitled Project"),
                        description=sp.get("description", ""),
                        category=cat,
                        project_role=sp.get("project_role", ""),
                        tools_used=sp.get("tools_used", ""),
                        process_steps=sp.get("process_steps", ""),
                        display_order=max_order,
                    )
                if template.get("suggested_skills"):
                    portfolio.skills = template["suggested_skills"]
                if template.get("suggested_interests"):
                    portfolio.design_interests = template["suggested_interests"]
                portfolio.save()
                messages.success(
                    request,
                    f'Template "{template["name"]}" applied. Edit your new projects and add your designs.',
                )
            else:
                messages.error(request, "Invalid template.")
            return redirect("student_portfolio_dashboard")

        elif action == "toggle_featured":
            project_id = request.POST.get("project_id")
            project = get_object_or_404(
                StudentPortfolioProject,
                pk=project_id,
                portfolio=portfolio,
            )
            project.featured = not project.featured
            project.save(update_fields=["featured", "updated_at"])
            state = "featured" if project.featured else "not featured"
            messages.info(request, f'"{project.title}" is now {state}.')
            return redirect("student_portfolio_dashboard")

        elif action == "delete_project":
            project_id = request.POST.get("project_id")
            project = get_object_or_404(
                StudentPortfolioProject,
                pk=project_id,
                portfolio=portfolio,
            )
            project_title = project.title
            project.delete()
            messages.success(request, f'Deleted "{project_title}".')
            return redirect("student_portfolio_dashboard")

        elif action == "update_custom_domain":
            sub = getattr(request.user, "student_portfolio_subscription", None)
            if sub and sub.is_active:
                domain = (request.POST.get("custom_domain") or "").strip().lower()
                if domain and domain.startswith("www."):
                    domain = domain[4:]
                portfolio.custom_domain = domain or None
                portfolio.save()
                messages.success(
                    request,
                    f"Custom domain set to {portfolio.custom_domain or 'none'}. Add a CNAME record pointing to designrden.com."
                )
            else:
                messages.error(request, "Upgrade to Pro to use a custom domain.")
            return redirect("student_portfolio_dashboard")

    projects = (
        portfolio.projects.annotate(
            like_count=Count("likes", distinct=True),
            bookmark_count=Count("bookmarks", distinct=True),
            feedback_count=Count("feedback_entries", distinct=True),
        )
        .order_by("display_order", "-created_at")
    )
    public_url = reverse("student_portfolio_public", args=[portfolio.share_slug])
    share_url = request.build_absolute_uri(public_url)

    sub = StudentPortfolioSubscription.objects.filter(user=request.user).first()
    has_pro = sub and sub.is_active
    pro_plan = StudentPortfolioPlan.objects.filter(
        is_active=True,
        name=StudentPortfolioPlan.PLAN_KEY,
    ).first() or StudentPortfolioPlan.objects.filter(is_active=True).first()

    context = {
        "portfolio": portfolio,
        "portfolio_form": portfolio_form,
        "project_form": project_form,
        "projects": projects,
        "share_url": share_url,
        "public_url": public_url,
        "featured_count": projects.filter(featured=True).count(),
        "sample_templates": SAMPLE_TEMPLATES,
        "has_pro": has_pro,
        "pro_plan": pro_plan,
    }
    return render(
        request,
        "designer_portfolio/student_portfolio_dashboard.html",
        context,
    )


@login_required
@require_POST
def student_portfolio_reorder_projects(request):
    portfolio = _get_or_create_portfolio(request.user)
    try:
        payload = json.loads((request.body or b"{}").decode("utf-8"))
    except (TypeError, ValueError, UnicodeDecodeError):
        return JsonResponse({"error": "Invalid JSON payload."}, status=400)

    project_ids = payload.get("project_ids") or []
    if not isinstance(project_ids, list):
        return JsonResponse({"error": "project_ids must be a list."}, status=400)

    normalized_ids = []
    for value in project_ids:
        try:
            normalized_ids.append(int(value))
        except (TypeError, ValueError):
            return JsonResponse({"error": "project_ids must contain integers."}, status=400)

    owned_ids = list(portfolio.projects.values_list("id", flat=True))
    if sorted(normalized_ids) != sorted(owned_ids):
        return JsonResponse(
            {
                "error": "project_ids must include every project in the portfolio exactly once.",
            },
            status=400,
        )

    project_map = {
        project.id: project for project in portfolio.projects.filter(id__in=normalized_ids)
    }
    for index, project_id in enumerate(normalized_ids):
        project = project_map[project_id]
        project.display_order = index

    with transaction.atomic():
        StudentPortfolioProject.objects.bulk_update(
            project_map.values(),
            ["display_order"],
        )

    return JsonResponse({"status": "ok"})


def student_portfolio_pricing(request):
    """Framer-style pricing page for student portfolios."""
    plan = StudentPortfolioPlan.objects.filter(
        is_active=True,
        name=StudentPortfolioPlan.PLAN_KEY,
    ).first() or StudentPortfolioPlan.objects.filter(is_active=True).first()
    context = {
        "plan": plan,
        "sample_templates": SAMPLE_TEMPLATES,
    }
    return render(
        request,
        "designer_portfolio/student_portfolio_pricing.html",
        context,
    )


def student_portfolio_public_view(request, share_slug):
    portfolio = get_object_or_404(
        StudentPortfolio.objects.select_related("user"),
        share_slug=share_slug,
    )
    if (
        portfolio.visibility == StudentPortfolio.Visibility.PRIVATE
        and not request.user.is_authenticated
    ):
        login_url = reverse("login")
        return redirect(f"{login_url}?next={request.path}")

    projects = (
        StudentPortfolioProject.objects.filter(portfolio=portfolio)
        .annotate(
            like_count=Count("likes", distinct=True),
            bookmark_count=Count("bookmarks", distinct=True),
        )
        .prefetch_related(
            Prefetch(
                "feedback_entries",
                queryset=StudentProjectFeedback.objects.select_related("author"),
            ),
            "gallery_images",
        )
        .order_by("display_order", "-created_at")
    )
    projects_by_category = {}
    for project in projects:
        projects_by_category.setdefault(project.get_category_display(), []).append(project)

    liked_project_ids = set()
    bookmarked_project_ids = set()
    if request.user.is_authenticated:
        liked_project_ids = set(
            StudentProjectLike.objects.filter(
                user=request.user,
                project__portfolio=portfolio,
            ).values_list("project_id", flat=True)
        )
        bookmarked_project_ids = set(
            StudentProjectBookmark.objects.filter(
                user=request.user,
                project__portfolio=portfolio,
            ).values_list("project_id", flat=True)
        )

    public_url = reverse("student_portfolio_public", args=[portfolio.share_slug])
    share_url = request.build_absolute_uri(public_url)

    context = {
        "portfolio": portfolio,
        "projects": projects,
        "projects_by_category": projects_by_category,
        "liked_project_ids": liked_project_ids,
        "bookmarked_project_ids": bookmarked_project_ids,
        "is_owner": request.user.is_authenticated and request.user == portfolio.user,
        "classroom_review_mode": portfolio.visibility == StudentPortfolio.Visibility.PRIVATE,
        "share_url": share_url,
    }
    return render(
        request,
        "designer_portfolio/student_portfolio_public.html",
        context,
    )


@login_required
def student_portfolio_edit_project(request, project_id):
    portfolio = _get_or_create_portfolio(request.user)
    project = get_object_or_404(
        StudentPortfolioProject,
        pk=project_id,
        portfolio=portfolio,
    )
    form = StudentPortfolioProjectForm(instance=project)

    if request.method == "POST":
        form = StudentPortfolioProjectForm(
            request.POST,
            request.FILES,
            instance=project,
        )
        if form.is_valid():
            form.save()
            for i, img_file in enumerate(request.FILES.getlist("gallery_images") or []):
                StudentPortfolioProjectImage.objects.create(
                    project=project,
                    image=img_file,
                    display_order=project.gallery_images.count() + i,
                )
            messages.success(request, f'Project "{project.title}" updated.')
            return redirect("student_portfolio_dashboard")
        messages.error(request, "Please fix the form errors and try again.")

    gallery_images = project.gallery_images.order_by("display_order", "id")
    context = {
        "project": project,
        "form": form,
        "gallery_images": gallery_images,
    }
    return render(
        request,
        "designer_portfolio/student_portfolio_edit_project.html",
        context,
    )


@login_required
@require_POST
def student_portfolio_project_feedback(request, project_id):
    project = get_object_or_404(StudentPortfolioProject, pk=project_id)
    form = StudentProjectFeedbackForm(request.POST)
    if form.is_valid():
        feedback = form.save(commit=False)
        feedback.project = project
        feedback.author = request.user
        feedback.save()
        messages.success(request, "Feedback posted.")
    else:
        messages.error(request, "Please provide at least 10 characters of feedback.")

    fallback = reverse("student_portfolio_public", args=[project.portfolio.share_slug])
    return redirect(_resolve_next_url(request, fallback))


@login_required
@require_POST
def student_portfolio_project_like_toggle(request, project_id):
    project = get_object_or_404(StudentPortfolioProject, pk=project_id)
    like, created = StudentProjectLike.objects.get_or_create(
        project=project,
        user=request.user,
    )
    if not created:
        like.delete()

    fallback = reverse("student_portfolio_public", args=[project.portfolio.share_slug])
    return redirect(_resolve_next_url(request, fallback))


@login_required
@require_POST
def student_portfolio_project_bookmark_toggle(request, project_id):
    project = get_object_or_404(StudentPortfolioProject, pk=project_id)
    bookmark, created = StudentProjectBookmark.objects.get_or_create(
        project=project,
        user=request.user,
    )
    if not created:
        bookmark.delete()

    fallback = reverse("student_portfolio_public", args=[project.portfolio.share_slug])
    return redirect(_resolve_next_url(request, fallback))


def _draw_wrapped_text(
    pdf: canvas.Canvas,
    text: str,
    x: int,
    y: int,
    width: int,
    font_name: str = "Helvetica",
    font_size: int = 10,
    leading: int = 14,
) -> int:
    pdf.setFont(font_name, font_size)
    paragraphs = (text or "").splitlines() or [""]
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            y -= leading
            continue

        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if pdf.stringWidth(candidate, font_name, font_size) <= width:
                line = candidate
            else:
                pdf.drawString(x, y, line)
                y -= leading
                line = word
        pdf.drawString(x, y, line)
        y -= leading
    return y


@login_required
def student_portfolio_resume_pdf(request):
    portfolio = _get_or_create_portfolio(request.user)
    projects = portfolio.projects.order_by("-featured", "display_order", "-created_at")[:12]

    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=LETTER)
    width, height = LETTER
    left_margin = 56
    right_margin = width - 56
    y = height - 64

    full_name = request.user.get_full_name().strip() or request.user.username
    pdf.setTitle(f"{full_name} - Student Portfolio Resume")
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawString(left_margin, y, full_name)
    y -= 24

    pdf.setFont("Helvetica", 11)
    pdf.drawString(left_margin, y, f"Email: {request.user.email or 'Not provided'}")
    y -= 16
    pdf.drawString(left_margin, y, f"Portfolio template: {portfolio.get_template_style_display()}")
    y -= 24

    if portfolio.bio:
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(left_margin, y, "Professional Summary")
        y -= 16
        y = _draw_wrapped_text(
            pdf,
            portfolio.bio,
            left_margin,
            y,
            int(right_margin - left_margin),
            font_size=10,
        )
        y -= 8

    if portfolio.skills_list:
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(left_margin, y, "Skills")
        y -= 16
        y = _draw_wrapped_text(
            pdf,
            ", ".join(portfolio.skills_list),
            left_margin,
            y,
            int(right_margin - left_margin),
            font_size=10,
        )
        y -= 8

    if portfolio.interests_list:
        pdf.setFont("Helvetica-Bold", 13)
        pdf.drawString(left_margin, y, "Design Interests")
        y -= 16
        y = _draw_wrapped_text(
            pdf,
            ", ".join(portfolio.interests_list),
            left_margin,
            y,
            int(right_margin - left_margin),
            font_size=10,
        )
        y -= 8

    pdf.setFont("Helvetica-Bold", 13)
    if y < 120:
        pdf.showPage()
        y = height - 64
    pdf.drawString(left_margin, y, "Selected Projects")
    y -= 16

    for project in projects:
        if y < 120:
            pdf.showPage()
            y = height - 64

        pdf.setFont("Helvetica-Bold", 11)
        project_header = f"{project.title} ({project.get_category_display()})"
        if project.featured:
            project_header += " - Featured"
        pdf.drawString(left_margin, y, project_header)
        y -= 14

        details = f"Role: {project.project_role or 'Not specified'} | Tools: {project.tools_used or 'Not specified'}"
        y = _draw_wrapped_text(
            pdf,
            details,
            left_margin + 10,
            y,
            int(right_margin - left_margin - 10),
            font_size=9,
            leading=12,
        )

        if project.description:
            y = _draw_wrapped_text(
                pdf,
                project.description,
                left_margin + 10,
                y,
                int(right_margin - left_margin - 10),
                font_size=9,
                leading=12,
            )
        y -= 8

    pdf.showPage()
    pdf.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"{request.user.username}-student-portfolio-resume.pdf"
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
