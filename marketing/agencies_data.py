"""Copy and feature catalog for the Agencies / Enterprise functionality page."""

from __future__ import annotations

AGENCIES_HERO = {
    "eyebrow": "For agencies & studios",
    "title": "Run your roster, productions, and client work on Global Designer Hub",
    "lead": (
        "designrden (drden) is the operating layer for fashion and creative agencies — "
        "discover talent, manage portfolios and tech packs, publish branded sites, sponsor "
        "community programs, and keep clients, producers, and designers aligned in one place."
    ),
}

AGENCIES_STATS = (
    {"value": "700+", "label": "Designers & creatives"},
    {"value": "3", "label": "Membership tiers"},
    {"value": "24/7", "label": "Cloud portfolios"},
    {"value": "1 hub", "label": "Talent to production"},
)

AGENCIES_WORKFLOW = (
    {
        "step": "01",
        "title": "Discover & shortlist",
        "body": "Search designers, collections, and events. Feature emerging talent and build rosters your producers can trust.",
        "url_name": "unified_search",
        "cta": "Search the hub",
    },
    {
        "step": "02",
        "title": "Collaborate in context",
        "body": "Share tech packs, message in-platform, and route custom orders without losing version history or client notes.",
        "url_name": "designer_dashboard",
        "cta": "Open dashboard",
    },
    {
        "step": "03",
        "title": "Publish & grow",
        "body": "Launch agency microsites, sponsor competitions, and activate memberships that unlock team profiles and analytics.",
        "url_name": "membership_upgrade",
        "cta": "View plans",
    },
)

AGENCIES_FEATURE_GROUPS = (
    {
        "id": "talent",
        "title": "Talent discovery & portfolios",
        "summary": "Find the right creative faster and review work the way production teams actually need it.",
        "features": (
            {
                "icon": "fa-magnifying-glass",
                "title": "Unified search",
                "description": "Filter designers, collections, and fashion events from one search bar on the homepage.",
                "url_name": "unified_search",
                "link_label": "Search drden",
            },
            {
                "icon": "fa-rocket",
                "title": "Startup & emerging talent",
                "description": "Browse featured emerging designers and sponsor spotlight programs for new graduates.",
                "url_name": "emerging_talent_list",
                "link_label": "Emerging talent",
                "url_namespace": "marketing",
            },
            {
                "icon": "fa-id-card",
                "title": "Designer portfolios",
                "description": "Public profiles with collections, lookbooks, process imagery, and publication-ready presentation.",
                "url_name": "designers_list",
                "link_label": "Browse designers",
            },
            {
                "icon": "fa-file-lines",
                "title": "Tech pack library",
                "description": "Store PDF and Excel tech packs per design so producers, factories, and clients access the latest spec.",
                "url_name": "designer_dashboard",
                "link_label": "Tech packs in dashboard",
            },
        ),
    },
    {
        "id": "studio",
        "title": "Studio operations & branded presence",
        "summary": "Give every desk a professional home — from solo leads to multi-seat studios.",
        "features": (
            {
                "icon": "fa-palette",
                "title": "Site builder",
                "description": "Drag-and-drop pages, AI-assisted layouts, and publishable microsites for agencies and lead designers.",
                "url_name": "builder_sites_list",
                "link_label": "Launch site builder",
            },
            {
                "icon": "fa-users",
                "title": "Team profiles",
                "description": "Premium Fashion Studio memberships support multi-page sites and team rosters for growing agencies.",
                "url_name": "membership_upgrade",
                "link_label": "Premium studio plan",
            },
            {
                "icon": "fa-globe",
                "title": "Custom domains & SEO",
                "description": "Personal designer websites include hosting, SSL, SEO tooling, and lead-capture forms.",
                "url_name": "membership_upgrade",
                "link_label": "Website memberships",
            },
            {
                "icon": "fa-chart-line",
                "title": "Analytics & visibility",
                "description": "Priority placement, advanced analytics, and featured profile options for client-facing studios.",
                "url_name": "membership_upgrade",
                "link_label": "Compare tiers",
            },
        ),
    },
    {
        "id": "production",
        "title": "Production & client delivery",
        "summary": "Move from moodboard to manufacturing with fewer email threads and clearer handoffs.",
        "features": (
            {
                "icon": "fa-shirt",
                "title": "Custom orders",
                "description": "Structured dress and custom-garment order flows connect clients, designers, and production status updates.",
                "url_name": "neworders_dresses",
                "link_label": "Custom orders",
            },
            {
                "icon": "fa-envelope",
                "title": "Messenger & notifications",
                "description": "In-platform messaging and dashboard alerts keep approvals and revisions in one thread.",
                "url_name": "messenger_list",
                "link_label": "Open messenger",
            },
            {
                "icon": "fa-store",
                "title": "Marketplace collections",
                "description": "Showcase shoppable or editorial collections that agencies can pitch to buyers and brand partners.",
                "url_name": "collections",
                "link_label": "Marketplace",
            },
            {
                "icon": "fa-mobile-screen",
                "title": "Mobile app",
                "description": "Review tech packs, lookbooks, and approvals from iOS or Android when teams are on the road.",
                "url_name": "iphone_app",
                "link_label": "Get the app",
            },
        ),
    },
    {
        "id": "community",
        "title": "Community, events & partnerships",
        "summary": "Activate drden audiences for campaigns, education, and long-term brand building.",
        "features": (
            {
                "icon": "fa-comments",
                "title": "Designer forum",
                "description": "Moderated community discussions, AMAs, and knowledge sharing across fashion disciplines.",
                "url_name": "forum_index",
                "link_label": "Community forum",
            },
            {
                "icon": "fa-calendar-days",
                "title": "Events & workshops",
                "description": "Host webinars, design jams, and virtual meetups — register attendees and archive replays.",
                "url_name": "events_list",
                "link_label": "Upcoming events",
                "url_namespace": "marketing",
            },
            {
                "icon": "fa-handshake",
                "title": "Brand partnerships",
                "description": "Run competitions, capsule collaborations, scholarship grants, and mentorship sponsorships.",
                "url_name": "brand_partner",
                "link_label": "Pitch a partnership",
                "url_namespace": "marketing",
            },
            {
                "icon": "fa-graduation-cap",
                "title": "Academy & mentorship",
                "description": "Student programs, mentor matching, and VolumeOne stories that surface the next generation.",
                "url_name": "student_page",
                "link_label": "Academy",
            },
        ),
    },
    {
        "id": "platform",
        "title": "Platform intelligence & growth",
        "summary": "AI-assisted workflows, referrals, and membership billing built for creative businesses.",
        "features": (
            {
                "icon": "fa-wand-magic-sparkles",
                "title": "Designer AI",
                "description": "In-dashboard assistant for collection planning, tech pack guidance, and production Q&A.",
                "url_name": "designer_dashboard",
                "link_label": "Try Designer AI",
            },
            {
                "icon": "fa-layer-group",
                "title": "Portfolio templates",
                "description": "Classic, modern, and minimal portfolio themes agencies can deploy for every roster member.",
                "url_name": "signup",
                "link_label": "Create accounts",
            },
            {
                "icon": "fa-gift",
                "title": "Referral network",
                "description": "Invite designers and partners with trackable referral links and onboarding perks.",
                "url_name": "signup",
                "link_label": "Start referring",
            },
            {
                "icon": "fa-credit-card",
                "title": "Stripe memberships",
                "description": "Monthly or yearly billing for Professional, Personal Website, and Premium Studio tiers.",
                "url_name": "membership_upgrade",
                "link_label": "Membership checkout",
            },
        ),
    },
)

AGENCIES_PLANS = (
    {
        "name": "Professional Portfolio",
        "tagline": "Core hub profile for every seat on your roster.",
        "highlights": ("Unlimited uploads", "Tech pack storage", "Featured visibility", "Client inquiries"),
    },
    {
        "name": "Personal Designer Website",
        "tagline": "Branded sites with hosting, SEO, and lead tools.",
        "highlights": ("Custom branding", "Blog & collections", "Hosting included", "Lead generation"),
        "recommended": True,
    },
    {
        "name": "Premium Fashion Studio",
        "tagline": "Agency-grade multi-page presence and team workflows.",
        "highlights": ("Team profiles", "Advanced analytics", "Custom domain", "Priority support"),
    },
)

AGENCIES_CTAS = (
    {
        "label": "Book an agency demo",
        "url_name": "brand_partner",
        "url_namespace": "marketing",
        "style": "primary",
    },
    {"label": "Create a free account", "url_name": "signup", "style": "ghost"},
)
