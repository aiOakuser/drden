"""
Management command to test email configuration
"""
from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings


class Command(BaseCommand):
    help = 'Test email configuration by sending a test email'

    def add_arguments(self, parser):
        parser.add_argument(
            'recipient',
            type=str,
            help='Email address to send test email to'
        )

    def handle(self, *args, **options):
        recipient = options['recipient']
        
        self.stdout.write(f'Sending test email to {recipient}...')
        self.stdout.write(f'Email backend: {settings.EMAIL_BACKEND}')
        
        if 'console' in settings.EMAIL_BACKEND.lower():
            self.stdout.write(self.style.WARNING(
                'Using console email backend - emails will print to console instead of sending'
            ))
        else:
            self.stdout.write(f'SMTP Host: {settings.EMAIL_HOST}')
            self.stdout.write(f'SMTP Port: {settings.EMAIL_PORT}')
            self.stdout.write(f'From Email: {settings.DEFAULT_FROM_EMAIL}')
        
        try:
            send_mail(
                subject='Test Email from designrden',
                message='This is a test email to verify your email configuration is working correctly.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[recipient],
                fail_silently=False,
            )
            
            self.stdout.write(self.style.SUCCESS(f'✓ Test email sent successfully to {recipient}'))
            
            if 'console' in settings.EMAIL_BACKEND.lower():
                self.stdout.write(self.style.WARNING(
                    'Check the console output above for the email content'
                ))
            else:
                self.stdout.write(self.style.SUCCESS(
                    f'Check the inbox for {recipient}'
                ))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Failed to send email: {str(e)}'))
            self.stdout.write(self.style.ERROR(
                '\nTroubleshooting tips:'
                '\n1. Check EMAIL_HOST_USER and EMAIL_HOST_PASSWORD in .env'
                '\n2. Ensure EMAIL_HOST and EMAIL_PORT are correct'
                '\n3. For Gmail, use an App Password (not your regular password)'
                '\n4. Check firewall settings for SMTP port access'
            ))
