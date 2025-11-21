"""
Management command to set up Adobe packages and products with initial data.
"""
from django.core.management.base import BaseCommand
from designer_portfolio.models import AdobeProduct, AdobePackage


class Command(BaseCommand):
    help = 'Set up Adobe products and packages with initial data'

    def handle(self, *args, **options):
        self.stdout.write('Setting up Adobe products and packages...')

        # Create Adobe Products
        products = [
            {
                'name': 'photoshop',
                'display_name': 'Adobe Photoshop',
                'description': 'Industry-standard photo and design software',
                'product_icon': '🎨',
                'is_popular': True,
                'order': 1
            },
            {
                'name': 'illustrator',
                'display_name': 'Adobe Illustrator',
                'description': 'Vector graphics and illustration software',
                'product_icon': '✏️',
                'is_popular': True,
                'order': 2
            },
            {
                'name': 'indesign',
                'display_name': 'Adobe InDesign',
                'description': 'Professional desktop publishing software',
                'product_icon': '📐',
                'is_popular': True,
                'order': 3
            },
            {
                'name': 'premiere_pro',
                'display_name': 'Adobe Premiere Pro',
                'description': 'Professional video editing software',
                'product_icon': '🎬',
                'is_popular': True,
                'order': 4
            },
            {
                'name': 'after_effects',
                'display_name': 'Adobe After Effects',
                'description': 'Motion graphics and visual effects software',
                'product_icon': '⚡',
                'is_popular': True,
                'order': 5
            },
            {
                'name': 'dreamweaver',
                'display_name': 'Adobe Dreamweaver',
                'description': 'Web design and development software',
                'product_icon': '🌐',
                'is_popular': False,
                'order': 6
            },
            {
                'name': 'lightroom',
                'display_name': 'Adobe Lightroom',
                'description': 'Photo editing and organization software',
                'product_icon': '📸',
                'is_popular': True,
                'order': 7
            },
            {
                'name': 'xd',
                'display_name': 'Adobe XD',
                'description': 'UI/UX design and prototyping software',
                'product_icon': '🎯',
                'is_popular': True,
                'order': 8
            },
            {
                'name': 'audition',
                'display_name': 'Adobe Audition',
                'description': 'Professional audio editing software',
                'product_icon': '🎵',
                'is_popular': False,
                'order': 9
            },
            {
                'name': 'animate',
                'display_name': 'Adobe Animate',
                'description': '2D animation and interactive content software',
                'product_icon': '🎭',
                'is_popular': False,
                'order': 10
            }
        ]

        for product_data in products:
            product, created = AdobeProduct.objects.get_or_create(
                name=product_data['name'],
                defaults=product_data
            )
            if created:
                self.stdout.write(f'Created product: {product.display_name}')

        # Create Adobe Packages
        packages = [
            {
                'package_type': 'single',
                'display_name': 'Single Product',
                'description': 'Perfect for focused work with one Adobe application',
                'product_count': 1,
                'monthly_price': 4.99,
                'is_popular': False,
                'order': 1
            },
            {
                'package_type': 'duo',
                'display_name': 'Duo Package',
                'description': 'Great combination for versatile designers',
                'product_count': 2,
                'monthly_price': 8.99,
                'is_popular': False,
                'order': 2
            },
            {
                'package_type': 'trio',
                'display_name': 'Trio Package',
                'description': 'Best balance of variety and value',
                'product_count': 3,
                'monthly_price': 12.99,
                'is_popular': True,
                'order': 3
            },
            {
                'package_type': 'quad',
                'display_name': 'Quad Package',
                'description': 'Comprehensive creative toolkit for professionals',
                'product_count': 4,
                'monthly_price': 16.99,
                'is_popular': False,
                'order': 4
            },
            {
                'package_type': 'penta',
                'display_name': 'Penta Package',
                'description': 'Professional creative suite for advanced users',
                'product_count': 5,
                'monthly_price': 20.99,
                'is_popular': False,
                'order': 5
            },
            {
                'package_type': 'hexa',
                'display_name': 'Hexa Package',
                'description': 'Extended creative suite with six applications',
                'product_count': 6,
                'monthly_price': 24.99,
                'is_popular': False,
                'order': 6
            },
            {
                'package_type': 'full',
                'display_name': 'Full Creative Suite',
                'description': 'Complete access to all Adobe Creative Cloud applications',
                'product_count': 10,
                'monthly_price': 29.99,
                'is_popular': False,
                'order': 7
            }
        ]

        for package_data in packages:
            package, created = AdobePackage.objects.get_or_create(
                package_type=package_data['package_type'],
                defaults=package_data
            )
            if created:
                self.stdout.write(f'Created package: {package.display_name}')

        # Set up suggested products for packages
        try:
            photoshop = AdobeProduct.objects.get(name='photoshop')
            illustrator = AdobeProduct.objects.get(name='illustrator')
            indesign = AdobeProduct.objects.get(name='indesign')
            premiere_pro = AdobeProduct.objects.get(name='premiere_pro')
            after_effects = AdobeProduct.objects.get(name='after_effects')
            lightroom = AdobeProduct.objects.get(name='lightroom')
            xd = AdobeProduct.objects.get(name='xd')

            # Set suggested products for trio package (most popular)
            trio_package = AdobePackage.objects.get(package_type='trio')
            trio_package.suggested_products.set([photoshop, illustrator, indesign])

            # Set suggested products for quad package
            quad_package = AdobePackage.objects.get(package_type='quad')
            quad_package.suggested_products.set([photoshop, illustrator, indesign, premiere_pro])

            # Set suggested products for penta package
            penta_package = AdobePackage.objects.get(package_type='penta')
            penta_package.suggested_products.set([photoshop, illustrator, indesign, premiere_pro, after_effects])

            self.stdout.write('Set up suggested products for packages')

        except AdobeProduct.DoesNotExist:
            self.stdout.write('Warning: Could not set up suggested products - some products missing')

        self.stdout.write(self.style.SUCCESS('Successfully set up Adobe packages and products!'))