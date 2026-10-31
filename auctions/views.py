from decimal import Decimal, InvalidOperation

from django.contrib.auth import authenticate, login, logout
from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse

from .models import User, Listing, Bid, Comment, Watchlist


def index(request):
    listings = Listing.objects.filter(is_active=True)

    for listing in listings:
        highest_bid = listing.bids.all().order_by("-amount").first()

        if highest_bid and highest_bid.amount > listing.starting_bid:
            listing.current_bid = highest_bid.amount
        else:
            listing.current_bid = listing.starting_bid

    return render(request, "auctions/index.html", {
        "listings": listings
    })


def listing(request, listing_id):
    listing = get_object_or_404(Listing, id=listing_id)

    bids = listing.bids.all().order_by("-amount")
    highest_bid = listing.starting_bid

    if bids.exists():
        highest_bid = max(highest_bid, bids.first().amount)

    winner = None

    if not listing.is_active and bids.exists():
        winner = bids.first()

    message = None

    if request.method == "POST":
        if not request.user.is_authenticated:
            return HttpResponseRedirect(reverse("login"))

        action = request.POST.get("action")

        if action == "bid":
            if not listing.is_active:
                message = "This auction is closed."

            elif request.user == listing.owner:
                message = "You cannot bid on your own listing."

            else:
                try:
                    amount = Decimal(request.POST.get("bid", ""))

                    if not amount.is_finite() or amount <= 0:
                        message = "Please enter a valid bid."

                    elif amount <= highest_bid:
                        message = "Your bid must be higher than the current bid."

                    else:
                        Bid.objects.create(
                            listing=listing,
                            bidder=request.user,
                            amount=amount
                        )

                        return HttpResponseRedirect(
                            reverse("listing", args=[listing.id])
                        )

                except (InvalidOperation, TypeError):
                    message = "Please enter a valid bid."

        elif action == "comment":
            comment_text = request.POST.get("comment", "").strip()

            if comment_text:
                Comment.objects.create(
                    listing=listing,
                    author=request.user,
                    message=comment_text
                )

                return HttpResponseRedirect(
                    reverse("listing", args=[listing.id])
                )

            message = "Comment cannot be empty."

        elif action == "watchlist":
            item = Watchlist.objects.filter(
                user=request.user,
                listing=listing
            )

            if item.exists():
                item.delete()
            else:
                Watchlist.objects.create(
                    user=request.user,
                    listing=listing
                )

            return HttpResponseRedirect(
                reverse("listing", args=[listing.id])
            )

    comments = listing.comments.all().order_by("-created_at")

    in_watchlist = False

    if request.user.is_authenticated:
        in_watchlist = Watchlist.objects.filter(
            user=request.user,
            listing=listing
        ).exists()

    return render(request, "auctions/listing.html", {
        "listing": listing,
        "highest_bid": highest_bid,
        "message": message,
        "bids": bids,
        "winner": winner,
        "comments": comments,
        "in_watchlist": in_watchlist
    })


def watchlist_view(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))

    items = Watchlist.objects.filter(user=request.user)

    return render(request, "auctions/watchlist.html", {
        "items": items
    })


def categories_view(request):
    categories = Listing.objects.exclude(
        category=""
    ).values_list("category", flat=True).distinct()

    return render(request, "auctions/categories.html", {
        "categories": categories
    })


def category_view(request, category_name):
    listings = Listing.objects.filter(
        category__iexact=category_name,
        is_active=True
    )

    return render(request, "auctions/category.html", {
        "category_name": category_name,
        "listings": listings
    })


def create_listing(request):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        description = request.POST.get("description", "").strip()
        starting_bid = request.POST.get("starting_bid", "")
        image_url = request.POST.get("image_url", "").strip()
        category = request.POST.get("category", "").strip()

        if not title or not description:
            return render(request, "auctions/create.html", {
                "message": "Title and description cannot be empty."
            })

        try:
            starting_bid = Decimal(starting_bid)

            if not starting_bid.is_finite() or starting_bid <= 0:
                raise InvalidOperation

        except (InvalidOperation, TypeError):
            return render(request, "auctions/create.html", {
                "message": "Please enter a valid starting bid."
            })

        Listing.objects.create(
            title=title,
            description=description,
            starting_bid=starting_bid,
            image_url=image_url,
            category=category,
            owner=request.user
        )

        return HttpResponseRedirect(reverse("index"))

    return render(request, "auctions/create.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST["username"]
        password = request.POST["password"]

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return HttpResponseRedirect(reverse("index"))

        return render(request, "auctions/login.html", {
            "message": "Invalid username and/or password."
        })

    return render(request, "auctions/login.html")


def logout_view(request):
    logout(request)
    return HttpResponseRedirect(reverse("index"))


def register(request):
    if request.method == "POST":
        username = request.POST["username"]
        email = request.POST["email"]
        password = request.POST["password"]
        confirmation = request.POST["confirmation"]

        if password != confirmation:
            return render(request, "auctions/register.html", {
                "message": "Passwords must match."
            })

        try:
            user = User.objects.create_user(
                username,
                email,
                password
            )
        except IntegrityError:
            return render(request, "auctions/register.html", {
                "message": "Username already taken."
            })

        login(request, user)
        return HttpResponseRedirect(reverse("index"))

    return render(request, "auctions/register.html")


def close_listing(request, listing_id):
    if not request.user.is_authenticated:
        return HttpResponseRedirect(reverse("login"))

    listing = get_object_or_404(Listing, id=listing_id)

    if request.method == "POST":
        if request.user == listing.owner and listing.is_active:
            listing.is_active = False
            listing.save()

    return HttpResponseRedirect(
        reverse("listing", args=[listing.id])
    )
