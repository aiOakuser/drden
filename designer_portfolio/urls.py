from django.urls import path, include
from django.views.generic.base import RedirectView
from rest_framework.routers import DefaultRouter
from . import views  # ✅ add this if you plan to call views.generate_techpack

from .views import (
    HomePageView,
    CollectionsPageView,
    CollectionViewSet,
    CollectionDetailView,
    DesignListView,
    DesignDetailView,
    EventListView,
    EventDetailView,
    upload_design,
    BrandViewSet,
    DesignViewSet,
    EventViewSet,
    PendingDesignersView,
    approve_designer,
    reject_designer,
    reinstate_designer,
    AboutView,
    AboutSiteView,
    contact_view,
    docs_index,
    docs_detail,
    DesignerDashboardView,
    designer_designs_view,
    designer_design_create_view,
    designer_design_edit_view,
    designer_design_delete_view,
    designer_design_detail_api,
    designer_about_me_view,
    designer_change_password_view,
    designer_contact_view,
    ProjectTemplateSelectionView,
    ProjectEditorView,
    VolumeOneView,
    VolumeOneShowcaseView,
    DesignerRegistrationView,
    DesignersListView,
    unified_search_view,
    designer_public_detail_view,
    designer_ai_chat,
    my_conversations,
    messenger_list,
    messenger_thread,
    messenger_start,
    PrivacyPolicyView,
    TermsOfServiceView,
    RefundPolicyView,
    GrievancePolicyView,
    DataRightsPolicyView,
    AccessibilityStatementView,
    ReportProblemView,
    ReportProblemThanksView,
    ForumIndexView,
    ForumCategoryView,
    ForumTopicView,
    ForumCreateTopicView,
    ForumCreatePostView,
    ForumSearchView,
    forum_bookmark_toggle,
    forum_post_like,
    forum_post_toggle_solution,
)

router = DefaultRouter()
router.register(r"brands", BrandViewSet, basename="brand")
router.register(r"collections", CollectionViewSet, basename="collection")
router.register(r"designs", DesignViewSet, basename="design")
router.register(r"events", EventViewSet, basename="event")

urlpatterns = [
    # Pages
    path("", HomePageView.as_view(), name="home"),
    
    # Collections
    path("collections/", CollectionsPageView.as_view(), name="collections"),
    path("collections/<slug:slug>/", CollectionDetailView.as_view(), name="collection_detail"),
    
    # Search (unified designers, collections, events)
    path("search/", unified_search_view, name="unified_search"),
    # Designers
    path("designers/", DesignersListView.as_view(), name="designers_list"),
    path("designers/<int:user_id>/", designer_public_detail_view, name="designer_public_detail"),
    
    path("designs/upload/", upload_design, name="upload_design"),  # 👈 Move this ABOVE
    path("designs/", DesignListView.as_view(), name="design_list"),
    path("designs/<slug:slug>/", DesignDetailView.as_view(), name="design_detail"),

    path("events/", EventListView.as_view(), name="event_list"),
    path("events/<slug:slug>/", EventDetailView.as_view(), name="event_detail"),
    
    path("about/", AboutView.as_view(), name="about"),
    path("about-site/", AboutSiteView.as_view(), name="about_site"),
    path("contact/", contact_view, name="contact"),
    
    # Community Forum
    path("community/", RedirectView.as_view(pattern_name="forum_index", permanent=False), name="community_redirect"),
    path("community/forum/", ForumIndexView.as_view(), name="forum_index"),
    path("community/forum/category/<slug:slug>/", ForumCategoryView.as_view(), name="forum_category"),
    path("community/forum/topic/<slug:slug>/", ForumTopicView.as_view(), name="forum_topic"),
    path("community/forum/new-topic/", ForumCreateTopicView.as_view(), name="forum_create_topic"),
    path("community/forum/topic/<slug:slug>/reply/", ForumCreatePostView.as_view(), name="forum_create_post"),
    path("community/forum/search/", ForumSearchView.as_view(), name="forum_search"),
    path("community/forum/bookmark/<slug:topic_slug>/", forum_bookmark_toggle, name="forum_bookmark_toggle"),
    path("community/forum/post/<int:post_id>/like/", forum_post_like, name="forum_post_like"),
    path("community/forum/post/<int:post_id>/solution/", forum_post_toggle_solution, name="forum_post_toggle_solution"),
    
    path("privacy/", PrivacyPolicyView.as_view(), name="privacy_policy"),
    path("terms/", TermsOfServiceView.as_view(), name="terms_of_service"),
    path("policies/refund-cancellation/", RefundPolicyView.as_view(), name="refund_policy"),
    path("policies/grievance-redressal/", GrievancePolicyView.as_view(), name="grievance_policy"),
    path("policies/data-rights/", DataRightsPolicyView.as_view(), name="data_rights_policy"),
    path("policies/accessibility/", AccessibilityStatementView.as_view(), name="accessibility_statement"),
    path("report-problem/", ReportProblemView.as_view(), name="report_problem"),
    path("report-problem/thanks/", ReportProblemThanksView.as_view(), name="report_problem_thanks"),
    path("docs/<slug:category_slug>/<slug:doc_slug>/", docs_detail, name="docs_detail"),
    path("docs/<slug:category_slug>/", docs_index, name="docs_category"),
    path("docs/", docs_index, name="docs_index"),
    
    # Designer Dashboard
    path("dashboard/", DesignerDashboardView.as_view(), name="designer_dashboard"),
    path("dashboard/designs/", designer_designs_view, name="designer_designs"),
    path("dashboard/designs/new/", designer_design_create_view, name="designer_design_create"),
    path("dashboard/designs/<int:design_id>/edit/", designer_design_edit_view, name="designer_design_edit"),
    path("dashboard/designs/<int:design_id>/delete/", designer_design_delete_view, name="designer_design_delete"),
    path("dashboard/designs/<int:design_id>/details/", designer_design_detail_api, name="designer_design_detail_api"),
    path("dashboard/about-me/", designer_about_me_view, name="designer_about_me"),
    path("dashboard/change-password/", designer_change_password_view, name="designer_change_password"),
    path("dashboard/contact/", designer_contact_view, name="designer_contact"),
    path("dashboard/projects/new/", ProjectTemplateSelectionView.as_view(), name="project_create"),
    path("dashboard/projects/<int:pk>/", ProjectEditorView.as_view(), name="project_editor"),
    path("volumeone/", VolumeOneShowcaseView.as_view(), name="volume_one_public"),
    path("dashboard/volumeone/", VolumeOneView.as_view(), name="volume_one"),
    # Common misspellings/legacy links -> redirect to dashboard
    path("dashephard/", RedirectView.as_view(pattern_name="designer_dashboard", permanent=False), name="dashephard"),
    path("dashepard/", RedirectView.as_view(pattern_name="designer_dashboard", permanent=False), name="dashepard"),
    
    

    # API
    path("api/", include(router.urls)),
    path("api/project-templates/", views.project_templates_api, name="project_templates_api"),
    path("api/projects/", views.create_project_api, name="project_create_api"),
    path("api/designers/register/", DesignerRegistrationView.as_view(), name="designer_register_api"),
    path("api/ai/designer-chat/", designer_ai_chat, name="designer_ai_chat"),
    path("designer-ai/history/", my_conversations, name="designer_ai_history"),

    # Messenger (registered users only)
    path("messenger/", messenger_list, name="messenger_list"),
    path("messenger/with/<int:user_id>/", messenger_start, name="messenger_start"),
    path("messenger/<int:conversation_id>/", messenger_thread, name="messenger_thread"),

    # Admin actions
    path("admin/pending-designers/", PendingDesignersView.as_view(), name="pending_designers"),
    path("admin/approve-designer/<int:user_id>/", approve_designer, name="approve_designer"),
    path("admin/reject-designer/<int:user_id>/", reject_designer, name="reject_designer"),
    path("admin/reinstate-designer/<int:designer_id>/", reinstate_designer, name="reinstate_designer"),

    # Subscription management
    path("subscription/", views.subscription_dashboard, name="subscription_dashboard"),
    path("subscription/change-plan/", views.change_subscription_plan, name="change_subscription_plan"),
    path("subscription/cancel/", views.cancel_subscription, name="cancel_subscription"),
    path("subscription/payment-methods/", views.payment_methods, name="payment_methods"),
    path("subscription/billing-history/", views.billing_history, name="billing_history"),
    
    # Payment processing
    path("payment/stripe/create-setup-intent/", views.create_stripe_setup_intent, name="create_stripe_setup_intent"),
    path("payment/stripe/webhook/", views.stripe_webhook, name="stripe_webhook"),
    path("payment/paypal/create-subscription/", views.create_paypal_subscription, name="create_paypal_subscription"),
    path("payment/paypal/webhook/", views.paypal_webhook, name="paypal_webhook"),

    # WebAuthn / Passkey endpoints
    path("webauthn/register/options/", views.webauthn_register_options, name="webauthn_register_options"),
    path("webauthn/register/verify/", views.webauthn_register_verify, name="webauthn_register_verify"),
    path("webauthn/authenticate/options/", views.webauthn_authenticate_options, name="webauthn_authenticate_options"),
    path("webauthn/authenticate/verify/", views.webauthn_authenticate_verify, name="webauthn_authenticate_verify"),
    path("webauthn/credentials/<int:credential_id>/delete/", views.webauthn_delete_credential, name="webauthn_delete_credential"),

     # ✅ Techpack generator route
    path("generate-techpack/<slug:slug>/", views.generate_techpack, name="generate_techpack"),
]
