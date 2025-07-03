import base64
import json
import logging
import os

import jwt
from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Count, Q

from .models import Auction, AuctionImage, Bid
from .serializers import (
    AuctionCreateSerializer,
    AuctionSerializer,
)

logger = logging.getLogger(__name__)


class AuctionConsumer(WebsocketConsumer):
    """WebSocket consumer for handling auction-related real-time communication."""

    GROUP_NAME = "auction"  # Constant for group name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
        self.username = None

    def connect(self):
        """Authenticate and establish WebSocket connection."""
        print("reach socket")

        try:
            token = self._extract_token()
            if not token:
                raise ValueError("No authentication token provided")

            self.user = self._authenticate_token(token)
            if not self.user:
                raise ValueError("Invalid authentication credentials")

            self._initialize_connection()
            self._join_group()
            logger.info(f"✅ Authenticated WebSocket connection for user: {self.user}")
            logger.info(f"{self.username} joined auction group.")

        except Exception as e:
            logger.error(f"🚨 WebSocket connection failed: {str(e)}")
            self.close()

    def disconnect(self, close_code):
        """Clean up on WebSocket disconnect."""
        if hasattr(self, "username") and self.username:
            self._leave_group()
            logger.info(f"User {self.username} disconnected with code: {close_code}")

    def receive(self, text_data):
        """Handle incoming WebSocket messages."""
        try:
            data = self._parse_message(text_data)
            handler = self._get_message_handler(data.get("source"))
            if handler:
                handler(data)
            else:
                self._send_error("Unsupported message type")

        except json.JSONDecodeError:
            self._send_error("Invalid message format")
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            self._send_error("Internal server error")

    # ----------------------
    #  Authentication Helpers
    # ----------------------

    def _extract_token(self):
        """Extract token from query string."""
        query_string = self.scope["query_string"].decode()
        if "tokens=" in query_string:
            return query_string.split("tokens=")[-1]
        return None

    def _authenticate_token(self, token):
        """Validate JWT token and return user."""
        try:
            payload = jwt.decode(
                token,
                os.getenv("JWT_SECRET_KEY"),
                algorithms=[os.getenv("JWT_ALGORITHM")],
                options={"verify_signature": False},
            )
            # print('auction verif: ',payload["user_id"])

            return get_user_model().objects.get(pk=payload["user_id"])
        except jwt.ExpiredSignatureError:
            print("🚨 Token expired")
        except jwt.DecodeError:
            print("🚨 Token invalid")
        except ObjectDoesNotExist:
            print("🚨 User not found")
        except Exception as e:
            print(f"🚨 Authentication error: {str(e)}")
        return None

    # ----------------------
    #  Group Management
    # ----------------------

    def _initialize_connection(self):
        """Set up user connection and groups."""
        self.scope["user"] = self.user
        self.username = self.user.username

        # Join user to their personal group
        async_to_sync(self.channel_layer.group_add)(self.username, self.channel_name)
        self.accept()

    def _join_group(self):
        """Add connection to auction group."""

        # Join common auction broadcast group
        async_to_sync(self.channel_layer.group_add)(self.GROUP_NAME, self.channel_name)

        # self.accept()

    def _leave_group(self):
        """Remove connection from auction group."""
        async_to_sync(self.channel_layer.group_discard)(
            self.GROUP_NAME, self.channel_name
        )

    # ----------------------
    #  Message Handlers
    # ----------------------

    def _parse_message(self, text_data):
        """Parse and validate incoming message."""
        data = json.loads(text_data)
        # print('client receive data: ', json.dumps(data, indent=2))
        # print('client receive data: ', data)
        if not isinstance(data, dict):
            raise ValueError("Message must be a JSON object")
        return data

    def _get_message_handler(self, message_type):
        """Get appropriate handler for message type."""
        handlers = {
            "search": self._handle_search,
            "FetchAuctionsListByCategory": self._handle_fetch_auctions_list_by_category,
            "create_auction": self._handle_create_auction,
            "place_bid": self._handle_place_bid,
            "watch_auction": self._handle_watch_auction,
            "delete_auction": self._handle_delete_auction,
            "edit_auction": self._handle_edit_auction,
            "close_auction": self._handle_close_auction,
            "reopen_auction": self._handle_reopen_auction,
            "report_user": self._handle_report_user,
            "load_more": self._handle_fetch_auctions_list_by_category,
            "likesAuctions": self._handle_fetch_likes_auctions,
            "bidsAuctions": self._handle_fetch_bids_auctions,
            "salesAuctions": self._handle_fetch_sales_auctions,
        }
        return handlers.get(message_type)

    def _handle_search(self, data):
        """Process auction search requests."""
        query = data.get("query", "").strip()

        # print('handle search: ',query)
        if not query:
            self._send_error("Empty search query")
            return

        auctions = self._search_auctions(query)
        # print('search auctions: ',auctions)

        serialized = AuctionSerializer(auctions, context={"user": self.user}, many=True)
        # print('serialized data: ',serialized.data)

        self._send_search_results(serialized.data)

    def _search_auctions(self, query):
        """Perform auction search query."""

        # print('search auction: ',query)
        return Auction.objects.filter(
            Q(title__istartswith=query) | Q(title__icontains=query)
        ).exclude(seller=self.user)

    def _handle_fetch_auctions_list_by_category(self, data):
        """Fetches a filtered list of auctions using optional filters."""
        user = self.user
        request_data = data.get("data", {})

        category = request_data.get("category")
        price = request_data.get("price")
        item_condition = request_data.get("itemCondition")
        popularity = request_data.get("popularity")
        posting_time = request_data.get("postingTime")

        page = request_data.get("page", 1)
        page_size = 5
        start = (page - 1) * page_size
        end = page * page_size + 1  # Fetch one extra to detect next page

        # Base queryset: exclude the seller's own auctions
        base_qs = Auction.objects.active().exclude(seller=user)

        # print("reach ", category)
        # Category filter
        if category and category.get("value") != "All":
            print("reach ")

            base_qs = base_qs.filter(category__id=category["key"])

            # print("auctions: ",base_qs)

        # Price sorting
        if price == "asc":
            base_qs = base_qs.order_by("current_price")
        elif price == "desc":
            base_qs = base_qs.order_by("-current_price")

        # Item condition filter
        if item_condition:
            base_qs = base_qs.filter(item_condition=item_condition)

        # Popularity sorting
        if popularity == "mostLikes":
            base_qs = base_qs.annotate(num_watchers=Count("watchers")).order_by(
                "-num_watchers"
            )
        elif popularity == "mostBids":
            base_qs = base_qs.annotate(num_bids=Count("bid")).order_by("-num_bids")

        # Posting time sorting
        if posting_time == "newest":
            base_qs = base_qs.order_by("-created_at")
        elif posting_time == "oldest":
            base_qs = base_qs.order_by("created_at")

        # print("auctions: ",base_qs)

        results = list(base_qs[start:end])
        has_next = len(results) > page_size
        paginated = results[:page_size]

        serialized = AuctionSerializer(paginated, context={"user": user}, many=True)
        next_page = page + 1 if has_next else None

        self._broadcast_to_user(
            "auctionsList",
            {
                "auctions": serialized.data,
                "nextPage": next_page,
                "loaded": page != 1,
            },
        )

    def _handle_create_auction(self, data):
        user = self.user
        data = data.get("data")
        images = data.pop("image", [])

        if not isinstance(images, list):
            raise ValueError("Image data must be a list")
        if len(images) > 3:
            raise ValueError("You can upload a maximum of 3 images")

        # Wrap everything in a transaction
        try:
            # Atomic operations (all succeeds or all fails)
            # Wrapped the entire operation in transaction.atomic() so if image saving fails, the auction creation is rolled back
            with transaction.atomic():
                # Create auction
                serializer = AuctionCreateSerializer(data=data, context={"user": user})

                if not serializer.is_valid():
                    error_msg = "Auction validation failed: " + str(serializer.errors)
                    raise ValueError(error_msg)

                new_auction = serializer.save()

                # Validate image data first before creating auction
                for idx, img_data in enumerate(images):
                    if not img_data.get("uri") or not img_data.get("fileName"):
                        raise ValueError(
                            f"Image at index {idx} is missing required data"
                        )

                    try:
                        base64_data = img_data.get("uri")
                        if "," in base64_data:
                            base64_data = base64_data.split(",")[1]
                        image_data = base64.b64decode(base64_data)
                    except (base64.binascii.Error, AttributeError) as e:
                        raise ValueError(
                            f"Invalid base64 image data at index {idx}"
                        ) from e

                    # Save auction image
                    try:
                        image_file = ContentFile(
                            image_data, name=img_data.get("fileName")
                        )
                        AuctionImage.objects.create(
                            auction=new_auction, image=image_file, is_primary=(idx == 0)
                        )
                        # AuctionImage.save()
                    except Exception as e:
                        raise ValueError(
                            f"Failed to save auction image: {str(e)}"
                        ) from e

                # Serialize the created auction
                broadcast_data = AuctionSerializer(
                    new_auction, context={"user": user}, many=False
                ).data

                # Broadcast to all connected users in the group
                self._broadcast_group("new_auction", broadcast_data)

                return new_auction

        except Exception as e:
            # Log the full error here if needed
            print(f"Error in auction creation: {str(e)}")
            raise  # Re-raise the exception after logging

    def _handle_place_bid(self, data):

        user = self.user
        data = data.get("data")
        auction_id = data.get("auction_id")
        current_price = data.get("current_price")

        try:
            auction = Auction.objects.get(pk=auction_id)
        except Auction.DoesNotExist:
            logger.error(f"Auction {auction_id} not found")
            self._send_error(f"Auction {auction_id} not found")
            return  # stop further execution

        # Check if user has already an existing bid
        new_amount = current_price + auction.bid_increment

        # print(new_amount)

        with transaction.atomic():
            try:
                bid, created = Bid.objects.get_or_create(
                    auction=auction, bidder=user, defaults={"amount": new_amount}
                )
                if not created:
                    bid.amount = new_amount
                    bid.save()

                auction.current_price = new_amount
                auction.save()

            except Exception as e:
                logger.exception(f"Error while placing bid: {str(e)}")
                self._send_error(f"Failed to place bid.: {str(e)}")
                return

        # Serialize and broadcast to group so all connected users see the update
        broadcast_data = AuctionSerializer(auction, context={"user": user}).data
        # print(broadcast_data)
        self._broadcast_group("new_bid", broadcast_data)

    def _handle_watch_auction(self, data):
        user = self.user
        data = data.get("data")
        auction_id = data.get("auction_id")

        try:
            auction = Auction.objects.get(pk=auction_id)
        except Auction.DoesNotExist:
            logger.error(f"Auction {auction_id} not found")
            self._send_error(f"Auction {auction_id} not found")
            return  # stop further execution

        # Check if user is a watcher
        is_watcher = auction.watchers.filter(pk=user.pk).exists()

        if is_watcher:
            auction.watchers.remove(user)
        else:
            auction.watchers.add(user)

        auction.save()

        # Serialize and broadcast to group so all connected users see the update
        broadcast_data = AuctionSerializer(auction, context={"user": user}).data
        # print(broadcast_data)
        self._broadcast_to_user("watcher", broadcast_data)

    def _handle_delete_auction(self, data):
        """Delete an auction and its images from S3"""
        auction_id = data.get("auction_id")
        user = self.user
        if not auction_id:
            self._send_error("No auction_id provided")
            return
        try:
            auction = Auction.objects.get(pk=auction_id)
        except Auction.DoesNotExist:
            self._send_error(f"Auction {auction_id} not found")
            return
        if auction.seller != user:
            self._send_error("Only the seller can delete the auction")
            return
        # Delete all images from S3 for this auction
        for img in auction.images.all():
            if img.image:
                img.image.delete(save=False)  # This deletes from S3
            img.delete()
        auction.delete()
        self._broadcast_to_user(
            "delete_auction",
            {"message": f"Auction {auction_id} and its images deleted successfully"}
        )

    def _handle_fetch_likes_auctions(self, data):

        user = self.user
        request_data = data.get("data", {})
        page = request_data.get("page", 1)
        page_size = 5

        start = (page - 1) * page_size
        end = page * page_size + 1  # Fetch one extra to check for next page

        # Base queryset: exclude the seller's own auctions
        base_qs = Auction.objects.likes(user).order_by("-created_at")

        # print(base_qs)

        results = list(base_qs[start:end])
        has_next = len(results) > page_size

        paginated_auctions = results[:page_size]  # Trim the extra item if it exists
        # print('reach: ', page, paginated_auctions)
        serialized = AuctionSerializer(
            paginated_auctions, context={"user": user}, many=True
        )

        next_page = page + 1 if has_next else None

        self._broadcast_to_user(
            "likesAuctions",
            {
                "auctions": serialized.data,
                "nextPage": next_page,
                "loaded": page != 1,
            },
        )

    def _handle_fetch_bids_auctions(self, data):

        user = self.user
        request_data = data.get("data", {})
        page = request_data.get("page", 1)
        page_size = 5

        start = (page - 1) * page_size
        end = page * page_size + 1  # Fetch one extra to check for next page

        # users latest bids auctions
        auctions = Auction.objects.user_latest_bids(user)

        # auctions = Auction.objects.filter(id__in=auction_ids)

        # print('_handle_fetch_bids_auctions: ',auctions)

        results = list(auctions[start:end])
        has_next = len(results) > page_size

        paginated_auctions = results[:page_size]  # Trim the extra item if it exists
        # print('reach: ', page, paginated_auctions)
        serialized = AuctionSerializer(
            paginated_auctions, context={"user": user}, many=True
        )

        next_page = page + 1 if has_next else None

        self._broadcast_to_user(
            "bidsAuctions",
            {
                "auctions": serialized.data,
                "nextPage": next_page,
                "loaded": page != 1,
            },
        )

    def _handle_fetch_sales_auctions(self, data):

        user = self.user
        request_data = data.get("data", {})
        page = request_data.get("page", 1)
        page_size = 5

        start = (page - 1) * page_size
        end = page * page_size + 1  # Fetch one extra to check for next page

        # users sales auctions
        user_sales = Auction.objects.sales(user).order_by("-created_at")

        # print('_handle_fetch_sales_auctions: ',user_sales)

        results = list(user_sales[start:end])
        has_next = len(results) > page_size

        paginated_auctions = results[:page_size]  # Trim the extra item if it exists
        # print('reach: ', page, paginated_auctions)
        serialized = AuctionSerializer(
            paginated_auctions, context={"user": user}, many=True
        )

        next_page = page + 1 if has_next else None

        self._broadcast_to_user(
            "salesAuctions",
            {
                "auctions": serialized.data,
                "nextPage": next_page,
                "loaded": page != 1,
            },
        )

    def _handle_edit_auction(self, data):
        pass

    def _handle_close_auction(self, data):
        pass

    def _handle_reopen_auction(self, data):
        pass

    def _handle_report_user(self, data):
        pass

    # ----------------------
    #  Response Methods
    # ----------------------

    def _send_search_results(self, results):
        """Send search results back to client."""
        # print('send from server to client: ',results)
        self.send(
            text_data=json.dumps(
                {"type": "search_results", "source": "search", "data": results}
            )
        )

    def _send_error(self, message):
        """Send error message to client."""
        self.send(text_data=json.dumps({"type": "error", "message": message}))

    def _reject_connection(self, reason):
        """Reject WebSocket connection with reason."""
        print(f"🚨 WebSocket rejected: {reason}")
        self.close()

    # ----------------------
    #  Group Broadcast Methods
    # ----------------------

    def _broadcast_to_user(self, source, data):
        """Send data to the user's personal group."""

        try:
            async_to_sync(self.channel_layer.group_send)(
                self.username,
                {"type": "broadcast.message", "source": source, "data": data},
            )
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")
            print(f"Error broadcasting message: {str(e)}")

    def _broadcast_group(self, source, data):
        """Handler for group broadcast messages."""
        try:
            # Broadcast to all connected users in the group
            async_to_sync(self.channel_layer.group_send)(
                self.GROUP_NAME,
                {"type": "broadcast.message", "source": source, "data": data},
            )
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")
            print(f"Error broadcasting message: {str(e)}")

    def broadcast_message(self, event):
        """Handle messages sent to the user's group."""
        try:
            self.send(
                text_data=json.dumps({"source": event["source"], "data": event["data"]})
            )
        except Exception as e:
            logger.error(f"Error broadcasting message: {str(e)}")
