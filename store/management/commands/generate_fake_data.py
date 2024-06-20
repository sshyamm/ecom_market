from django.core.management.base import BaseCommand
from faker import Faker
from store.models import Item, Category

class Command(BaseCommand):
    help = 'Generate fake data for Item model'

    def handle(self, *args, **options):
        fake = Faker()

        # Predefined list of item names
        item_names = [
            "American Eagle", "Maple Leaf", "Krugerrand", "Sovereign", "Liberty Head",
            "Buffalo Nickel", "Mercury Dime", "Morgan Dollar", "Peace Dollar", "Saint-Gaudens"
        ]

        # Fetch all category IDs
        category_ids = list(Category.objects.values_list('id', flat=True))

        for _ in range(10):
            # Choose a random item name from the predefined list
            item_name = fake.random_element(elements=item_names).title()

            # Randomly select one category ID
            random_category_id = fake.random_element(elements=category_ids)

            # Create an Item object with fake data
            item = Item(
                purpose = 'sale',
                item_name=item_name,
                item_desc=fake.sentence(),
                item_year=fake.random_int(min=1800, max=2023),
                item_country=fake.country(),
                item_material=fake.word(),
                rate=fake.random_number(digits=4),
                item_weight=fake.random_number(digits=2),
                item_status=fake.random_element(elements=('available', 'sold', 'pending'))
            )
            item.save()

            # Add the selected category ID to the item
            item.category.add(Category.objects.get(id=random_category_id))

            # Save the item with the category
            item.save()

        self.stdout.write(self.style.SUCCESS('Successfully generated fake data'))

'''from django.core.management.base import BaseCommand
from faker import Faker
from coins.models import Coin
from django.core.files.base import ContentFile
import requests
import os
from bs4 import BeautifulSoup
import re

class Command(BaseCommand):
    help = 'Generate fake data for Coin model'

    def handle(self, *args, **options):
        fake = Faker()

        # Predefined list of coin names
        coin_names = [
            "American Eagle", "Maple Leaf", "Krugerrand", "Sovereign", "Liberty Head",
            "Buffalo Nickel", "Mercury Dime", "Morgan Dollar", "Peace Dollar", "Saint-Gaudens"
        ]

        # Create the folder if it doesn't exist
        if not os.path.exists('media/coin_images'):
            os.makedirs('media/coin_images')

        for _ in range(10):
            # Generate a random search query
            search_query = "coin"

            # Generate a Google image search URL
            search_url = f"https://www.google.com/search?q={search_query}&tbm=isch"

            # Send a GET request to Google Images
            response = requests.get(search_url)
            soup = BeautifulSoup(response.content, 'html.parser')

            # Find all image elements
            images = soup.find_all('img')

            # Extract image URLs
            image_urls = [img['src'] for img in images if img.get('src')]

            # Filter image URLs to remove non-image links
            image_urls = [url for url in image_urls if re.match(r'^https?://', url)]

            # Choose a random image URL
            if image_urls:
                image_url = fake.random_element(elements=image_urls)
            else:
                image_url = "https://via.placeholder.com/400x400"  # Placeholder URL

            # Download the image from the URL
            image_response = requests.get(image_url)

            # Choose a random coin name from the predefined list
            coin_name = fake.random_element(elements=coin_names).title()

            # Create a Coin object with fake data
            coin = Coin(
                coin_name=coin_name,
                coin_desc=fake.sentence(),
                coin_year=fake.random_int(min=1800, max=2023),
                coin_country=fake.country(),
                coin_material=fake.word(),
                rate=fake.random_number(digits=4),
                coin_weight=fake.random_number(digits=2),
                starting_bid=fake.random_number(digits=3),
                coin_status=fake.random_element(elements=('available', 'sold', 'pending'))
            )

            # Save the image to the 'coin_images' folder
            image_path = f"media/coin_images/coin_{fake.random_number(digits=4)}.png"
            with open(image_path, 'wb') as image_file:
                image_file.write(image_response.content)

            # Assign the image path to the coin_image field
            coin.coin_image.save(os.path.basename(image_path), ContentFile(image_response.content), save=False)
            coin.save()

        self.stdout.write(self.style.SUCCESS('Successfully generated fake data'))'''
