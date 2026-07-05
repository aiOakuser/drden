from django.core.management.base import BaseCommand

from designer_portfolio.models import DocPage

SLUG = "media-guidelines"
TITLE = "Media Guidelines for Designers & Viewers"
CATEGORY = "designers"
TAGS = "media, images, video, pdf, upload, guidelines"

CONTENT = """These guidelines help designers publish polished, professional portfolios, and help viewers (recruiters, collaborators, mentors) know what to expect when reviewing a portfolio on designrden.

For Designers: What to Upload

Cover images and gallery images should be high-resolution JPG, PNG, or WebP files. Aim for at least 1600px on the longest edge so work reads clearly on both desktop and mobile.

Process videos should be MP4 or MOV format. Keep clips focused and under a few minutes — a short process reel communicates more than a long unedited walkthrough.

Project PDFs (techpacks, resumes, lookbooks) should be exported as standard PDF files, not scanned photos of documents.

The maximum upload size is 20MB per file. If an image or video is larger, compress it before uploading — most exporters (Photoshop "Save for Web", HandBrake for video) can hit this target without a visible quality loss.

For Designers: Presentation Best Practices

Order your gallery to tell a story: start with your strongest hero image, follow with process and detail shots, and close with the final result.

Use consistent lighting and backgrounds within a single project so the gallery reads as one cohesive body of work.

Caption images with what a viewer can't tell from the photo alone — material, technique, or the problem you were solving — rather than restating the obvious.

Only upload work you have the rights to publish, and credit collaborators (photographers, models, stylists, teammates) in your project description.

For Viewers: What to Expect

Public student and designer portfolios are curated selections of a designer's best work, not a complete archive — expect quality over quantity.

Process documentation (sketches, iterations, techpacks) is included when a designer wants to show how they think, not just what they made. Use it to evaluate process and craft, not only the final image.

If a portfolio isn't publicly visible, the designer may have kept it limited to classroom review rather than public recruiters — use the platform's contact options if you need access.

Report any content that looks miscredited, stolen, or inappropriate using the contact/report options on the platform so it can be reviewed."""


class Command(BaseCommand):
    help = "Create or update the /docs/designers/media-guidelines/ documentation page."

    def handle(self, *args, **options):
        doc, created = DocPage.objects.update_or_create(
            slug=SLUG,
            defaults={
                "title": TITLE,
                "content": CONTENT,
                "category": CATEGORY,
                "tags": TAGS,
                "published": True,
            },
        )
        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} doc page: {doc.title} (/docs/designers/{doc.slug}/)"))
