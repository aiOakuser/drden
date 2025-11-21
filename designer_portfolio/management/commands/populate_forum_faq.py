"""
Management command to populate forum with FAQ data
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from designer_portfolio.models import ForumCategory, ForumTopic
from django.utils.text import slugify

User = get_user_model()


class Command(BaseCommand):
    help = 'Populate forum with FAQ topics and initial content'

    def handle(self, *args, **options):
        # Get or create admin user for posting FAQs
        admin_user = User.objects.filter(is_staff=True).first()
        if not admin_user:
            admin_user = User.objects.filter(is_superuser=True).first()
        
        if not admin_user:
            self.stdout.write(self.style.ERROR('No admin user found. Please create a superuser first.'))
            return

        # FAQ Data
        faq_data = {
            'Portfolio & Showcase': [
                {
                    'title': 'What should a designer include in a professional portfolio?',
                    'content': '''A complete designer portfolio includes:

• **Professional bio + headshot**: Show who you are
• **6-10 best projects**: Quality over quantity
• **Detailed case studies**: Problem → Process → Solution → Results
• **Tools used**: Figma, Adobe XD, Sketch, etc.
• **Before-and-after visuals**: Show transformation
• **Client testimonials**: Build trust and credibility
• **Clear contact or booking link**: Make it easy to reach you

Focus on your strongest work that demonstrates your skills and design thinking process.'''
                },
                {
                    'title': 'How many projects should I show in my portfolio?',
                    'content': '''**Quality matters more than quantity.**

Show **6-10 strong, polished projects** instead of uploading every piece of work you've ever done.

Each project should:
• Reflect your best skills
• Include a case study
• Show your design process
• Demonstrate real results

Remember: Recruiters and clients spend only 2-3 minutes reviewing portfolios. Make every project count!'''
                },
                {
                    'title': 'What file formats and sizes are best for portfolio images?',
                    'content': '''**Recommended specifications:**

**Formats:**
• JPG - Good for photos
• PNG - Best for graphics with transparency
• WEBP - Optimal for web (best quality + small size)

**Dimensions:**
• Width: 1200-1600px
• For retina displays: 2× resolution

**File size:**
• Keep under 250 KB per image
• Use compression tools like TinyPNG or ImageOptim

**Pro tip:** WEBP format provides the best balance of quality and performance for web portfolios.'''
                },
                {
                    'title': 'How often should I update my portfolio?',
                    'content': '''**Update every 3 months** or after completing a significant project.

**What to update:**
• Hero banner with latest work
• Featured case study
• New client testimonials
• Skills and tools section
• Remove outdated projects

**Why it matters:**
• Shows you're actively working
• Demonstrates growth
• Keeps content fresh for returning visitors
• Improves SEO rankings

Set a calendar reminder to review your portfolio quarterly!'''
                },
            ],
            'Website Maintenance': [
                {
                    'title': 'How often should I back up my designer website?',
                    'content': '''**Backup frequency recommendations:**

**Static portfolio sites:**
• Weekly backups are sufficient
• Before major updates

**Dynamic sites with blog/uploads:**
• Daily automated backups
• Keep 30-day backup history

**Best practices:**
• Use cloud storage (Google Drive, Dropbox)
• Keep offline backups on external drive
• Test restore process regularly
• Backup both files and database

**Recommended tools:**
• UpdraftPlus (WordPress)
• cPanel backup tools
• Git for code versioning'''
                },
                {
                    'title': 'Why is my portfolio website slow?',
                    'content': '''**Common causes of slow performance:**

1. **Large images**
   • Unoptimized photos
   • No compression
   • High-resolution unnecessary for web

2. **Heavy media files**
   • Autoplay videos
   • Multiple embedded videos
   • Animated GIFs

3. **Code issues**
   • Unused CSS/JavaScript
   • No caching enabled
   • Render-blocking resources

4. **Hosting problems**
   • Shared hosting with limited resources
   • Server location far from visitors

**Solutions:**
✅ Compress all images
✅ Enable caching
✅ Lazy-load media
✅ Minify CSS/JS
✅ Use a CDN
✅ Upgrade hosting if needed'''
                },
                {
                    'title': 'How do I secure my portfolio website?',
                    'content': '''**Essential security measures:**

🔒 **SSL Certificate**
• Enable HTTPS everywhere
• Free certificates via Let's Encrypt

🔑 **Access Control**
• Use strong, unique passwords
• Enable two-factor authentication (2FA)
• Limit login attempts

🛡️ **Software Updates**
• Keep CMS/plugins updated
• Remove unused plugins
• Update dependencies regularly

🔍 **Monitoring**
• Regular malware scans
• Monitor suspicious activity
• Use security plugins (Wordfence, Sucuri)

☁️ **Hosting Security**
• Choose reputable hosting providers
• Enable firewall
• Regular automated backups

**Remember:** A hacked portfolio can damage your professional reputation. Security is not optional!'''
                },
            ],
            'UI/UX Design': [
                {
                    'title': 'What are key principles of good UI design?',
                    'content': '''**Essential UI design principles:**

1. **Consistency**
   • Uniform design patterns
   • Consistent spacing and sizing
   • Reusable components

2. **Visual Hierarchy**
   • Clear emphasis on important elements
   • Proper font sizes and weights
   • Effective use of color and contrast

3. **Spacing & Alignment**
   • Proper whitespace
   • Grid-based layouts
   • Aligned elements

4. **Intuitive Navigation**
   • Clear menu structure
   • Breadcrumbs for deep pages
   • Obvious CTAs

5. **Accessibility**
   • High contrast ratios (WCAG compliant)
   • Keyboard navigation
   • Screen reader support

6. **Responsive Design**
   • Mobile-first approach
   • Flexible grids
   • Touch-friendly targets'''
                },
                {
                    'title': 'How do I make my design responsive?',
                    'content': '''**Steps to create responsive designs:**

📱 **Mobile-First Approach**
• Design for mobile screens first
• Scale up for tablets and desktop
• Prioritize essential content

🎯 **Flexible Layouts**
• Use CSS Grid or Flexbox
• Fluid width containers (%, vw, rem)
• Avoid fixed pixel widths

📐 **Breakpoints**
• Mobile: 320-480px
• Tablet: 768-1024px
• Desktop: 1200px+

🖼️ **Responsive Images**
• Use srcset for multiple sizes
• Implement lazy loading
• Optimize for different densities

🧪 **Testing**
• Test on real devices
• Use browser dev tools
• Check different orientations

**Tools to help:**
• Tailwind CSS responsive utilities
• Bootstrap grid system
• Chrome DevTools device mode'''
                },
            ],
            'Client Relations': [
                {
                    'title': 'How do I deal with clients asking for unlimited revisions?',
                    'content': '''**Professional approach to revision requests:**

📋 **Prevention (Best Practice):**
• Set clear revision limits in contract (2-3 rounds typical)
• Define what counts as a revision
• Include scope in proposal

💬 **When it happens:**
1. **Remind politely** of agreed terms
2. **Explain** that additional revisions fall outside scope
3. **Offer** additional revision packages
4. **Document** all change requests

💰 **Pricing additional revisions:**
• Charge per hour
• Offer revision packages
• Require payment upfront

**Sample response:**
"As outlined in our agreement, the project includes 2 revision rounds. We've completed those. I'm happy to continue with additional revisions at $XX per hour or a package of 3 revisions for $XXX."

**Remember:** Clear boundaries protect both your time and the client relationship.'''
                },
                {
                    'title': 'What should I include in a design contract?',
                    'content': '''**Essential contract elements:**

📝 **Project Details**
• Scope of work
• Deliverables (formats, sizes, files)
• Timeline and milestones
• Number of concepts/revisions

💰 **Payment Terms**
• Total project cost
• Payment schedule (50% upfront common)
• Late payment fees
• Accepted payment methods

📋 **Responsibilities**
• Client provides: content, images, feedback
• Designer provides: designs, source files
• Communication expectations

⚖️ **Legal Protection**
• Copyright ownership
• Usage rights
• Confidentiality (NDA if needed)
• Termination clause
• Dispute resolution

🔄 **Change Management**
• How to request changes
• Additional fees for scope changes
• Approval process

**Pro tip:** Use contract templates from legal services or platforms like Bonsai, HoneyBook, or Dubsado.'''
                },
            ],
            'Community & Networking': [
                {
                    'title': 'What are the benefits of joining a designer community?',
                    'content': '''**Why designer communities matter:**

🤝 **Networking**
• Connect with peers globally
• Find collaboration opportunities
• Build lasting professional relationships

💡 **Learning & Growth**
• Get feedback on your work
• Learn from others' experiences
• Stay updated with trends and tools

💼 **Career Opportunities**
• Job leads and referrals
• Freelance project opportunities
• Partnership possibilities

🎨 **Inspiration**
• See diverse design approaches
• Discover new techniques
• Challenge yourself with community projects

🛠️ **Resources**
• Access to templates and tools
• Shared knowledge base
• Plugin and software recommendations

❤️ **Support**
• Motivation during tough projects
• Advice on client issues
• Mental health and work-life balance

**Popular communities:**
• GlobalDesignerHub (here!)
• Dribbble
• Behance
• Designer Hangout
• ADPList'''
                },
                {
                    'title': 'How do I ask for portfolio feedback in forums?',
                    'content': '''**Effective feedback request structure:**

📸 **Include visuals**
• Share screenshots or links
• Show multiple angles
• Highlight specific areas

🎯 **Be specific**
• What are you trying to achieve?
• What challenges are you facing?
• What specific aspect needs feedback?

📝 **Provide context**
• Project goal and target audience
• Tools and techniques used
• Constraints or limitations

❓ **Ask clear questions**
Instead of: "What do you think?"
Ask: "Does the visual hierarchy guide the eye effectively?"

**Good example:**
"Hi everyone! I'm redesigning a fitness app dashboard. My goal is to make workout tracking quick and motivating for beginners. I'm concerned about the color contrast and icon clarity. Do the CTAs stand out enough? Does the layout feel too cluttered? [image]"

**Tips:**
• Keep posts concise
• Be open to criticism
• Respond to feedback
• Show appreciation'''
                },
            ],
            'Technical Help': [
                {
                    'title': 'Why are my images not loading on the website?',
                    'content': '''**Common causes and solutions:**

🔗 **Incorrect file paths**
• Check relative vs absolute paths
• Verify folder structure
• Look for typos in filenames

📁 **File format issues**
• Use web-safe formats (JPG, PNG, WEBP, SVG)
• Avoid proprietary formats
• Check file extensions match actual format

📦 **File size problems**
• Large files may timeout
• Compress images under 1MB
• Use progressive JPEGs

🔒 **HTTPS/HTTP mixed content**
• All resources should use HTTPS
• Update old HTTP image URLs
• Check CDN SSL certificates

⚙️ **Server configuration**
• Verify upload limits
• Check file permissions
• Confirm MIME types configured

**Quick debugging:**
1. Open browser console (F12)
2. Check Network tab for 404 errors
3. Right-click image → "Inspect"
4. Verify src attribute is correct

**Test:** Try opening the image URL directly in browser to isolate the issue.'''
                },
                {
                    'title': 'Why is my contact form not working?',
                    'content': '''**Troubleshooting steps:**

📧 **Email configuration**
• Verify SMTP settings
• Check email credentials
• Test with different email addresses
• Confirm SPF/DKIM records

🔍 **Form validation**
• Check required fields are marked
• Verify email format validation
• Test with various inputs
• Check character limits

🖥️ **Backend issues**
• API endpoint responding?
• Server-side validation working?
• Check error logs
• Verify form action URL

🔒 **Security measures**
• CAPTCHA blocking submissions?
• CSRF token present?
• Firewall blocking requests?

📬 **Email delivery**
• Check spam folder
• Verify sender email not blacklisted
• Test email server settings
• Use email service (SendGrid, Mailgun)

**Debugging checklist:**
✅ Form submits without errors?
✅ Data reaching backend?
✅ Email sending function called?
✅ Recipient email correct?
✅ No email delivery errors in logs?

**Quick fix:** Use a form service like Formspree, Netlify Forms, or Google Forms as backup.'''
                },
            ],
        }

        created_count = 0
        
        for category_name, topics in faq_data.items():
            # Get or create category
            category = ForumCategory.objects.filter(name=category_name).first()
            
            if not category:
                self.stdout.write(self.style.WARNING(f'Category "{category_name}" not found. Skipping...'))
                continue
            
            for topic_data in topics:
                # Check if topic already exists
                slug = slugify(topic_data['title'])
                if ForumTopic.objects.filter(slug=slug).exists():
                    self.stdout.write(self.style.WARNING(f'Topic "{topic_data["title"]}" already exists. Skipping...'))
                    continue
                
                # Create topic
                topic = ForumTopic.objects.create(
                    category=category,
                    author=admin_user,
                    title=topic_data['title'],
                    slug=slug,
                    content=topic_data['content'],
                    is_pinned=True,  # Pin FAQ topics
                    is_active=True,
                )
                
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✓ Created: {topic.title}'))
        
        self.stdout.write(self.style.SUCCESS(f'\n🎉 Successfully created {created_count} FAQ topics!'))
        self.stdout.write(self.style.SUCCESS('Visit /community/forum/ to see them.'))
