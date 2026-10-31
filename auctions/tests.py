
from django.test import TestCase
from django.urls import reverse

from .models import User, Listing, Bid, Watchlist, Comment


class ListingTestCase(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            password="test123"
        )

        self.other_user = User.objects.create_user(
            username="otheruser",
            password="test123"
        )

        self.listing = Listing.objects.create(
            title="Test Laptop",
            description="A test laptop",
            starting_bid=200,
            category="Electronics",
            owner=self.user
        )

    def test_index_page(self):
        response = self.client.get(reverse("index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Laptop")

    def test_closed_listing_not_in_index(self):
        self.listing.is_active = False
        self.listing.save()

        response = self.client.get(reverse("index"))

        self.assertNotContains(response, "Test Laptop")

    def test_listing_page(self):
        response = self.client.get(
            reverse("listing", args=[self.listing.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Laptop")
        self.assertContains(response, "A test laptop")

    def test_register(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "password123",
            "confirmation": "password123"
        })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            User.objects.filter(username="newuser").exists()
        )

    def test_login(self):
        response = self.client.post(reverse("login"), {
            "username": "testuser",
            "password": "test123"
        })

        self.assertEqual(response.status_code, 302)
        self.assertIn("_auth_user_id", self.client.session)

    def test_place_bid(self):
        self.client.login(
            username="otheruser",
            password="test123"
        )

        response = self.client.post(
            reverse("listing", args=[self.listing.id]),
            {
                "action": "bid",
                "bid": "250"
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Bid.objects.filter(
                listing=self.listing,
                bidder=self.other_user,
                amount=250
            ).exists()
        )

    def test_invalid_bid(self):
        self.client.login(
            username="otheruser",
            password="test123"
        )

        response = self.client.post(
            reverse("listing", args=[self.listing.id]),
            {
                "action": "bid",
                "bid": "200"
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "Your bid must be higher than the current bid."
        )
        self.assertEqual(Bid.objects.count(), 0)

    def test_owner_cannot_bid(self):
        self.client.login(
            username="testuser",
            password="test123"
        )

        response = self.client.post(
            reverse("listing", args=[self.listing.id]),
            {
                "action": "bid",
                "bid": "250"
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "You cannot bid on your own listing."
        )
        self.assertEqual(Bid.objects.count(), 0)

    def test_add_to_watchlist(self):
        self.client.login(
            username="testuser",
            password="test123"
        )

        self.client.post(
            reverse("listing", args=[self.listing.id]),
            {"action": "watchlist"}
        )

        self.assertTrue(
            Watchlist.objects.filter(
                user=self.user,
                listing=self.listing
            ).exists()
        )

    def test_remove_from_watchlist(self):
        self.client.login(
            username="testuser",
            password="test123"
        )

        Watchlist.objects.create(
            user=self.user,
            listing=self.listing
        )

        self.client.post(
            reverse("listing", args=[self.listing.id]),
            {"action": "watchlist"}
        )

        self.assertFalse(
            Watchlist.objects.filter(
                user=self.user,
                listing=self.listing
            ).exists()
        )

    def test_add_comment(self):
        self.client.login(
            username="testuser",
            password="test123"
        )

        response = self.client.post(
            reverse("listing", args=[self.listing.id]),
            {
                "action": "comment",
                "comment": "This is a good laptop."
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Comment.objects.filter(
                listing=self.listing,
                author=self.user,
                message="This is a good laptop."
            ).exists()
        )

    def test_comment_display(self):
        Comment.objects.create(
            listing=self.listing,
            author=self.user,
            message="This is a good laptop."
        )

        response = self.client.get(
            reverse("listing", args=[self.listing.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "This is a good laptop.")
        self.assertContains(response, "testuser")

    def test_owner_can_close_listing(self):
        self.client.login(
            username="testuser",
            password="test123"
        )

        response = self.client.post(
            reverse("close", args=[self.listing.id])
        )

        self.listing.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertFalse(self.listing.is_active)

    def test_other_user_cannot_close_listing(self):
        self.client.login(
            username="otheruser",
            password="test123"
        )

        response = self.client.post(
            reverse("close", args=[self.listing.id])
        )

        self.listing.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.listing.is_active)

    def test_categories_page(self):
        response = self.client.get(reverse("categories"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Electronics")

    def test_category_page(self):
        response = self.client.get(
            reverse("category", args=["Electronics"])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Laptop")

    def test_guest_cannot_place_bid(self):
        response = self.client.post(
            reverse("listing", args=[self.listing.id]),
            {
                "action": "bid",
                "bid": "250"
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Bid.objects.count(), 0)

    def test_guest_cannot_add_comment(self):
        response = self.client.post(
            reverse("listing", args=[self.listing.id]),
            {
                "action": "comment",
                "comment": "Guest comment"
            }
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(Comment.objects.count(), 0)
