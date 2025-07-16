import uuid

from api.auctions.models import Auction
from api.users.models import User
from django.core.validators import MinLengthValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# Create your models here.


class Connection(models.Model):
    """Represents a bidirectional connection between two users for messaging."""

    class Meta:
        unique_together = [("sender", "receiver")]
        ordering = ["-updated"]
        verbose_name = _("Connection")
        verbose_name_plural = _("Connections")
        indexes = [
            models.Index(fields=["sender", "receiver"]),
            models.Index(fields=["updated"]),
        ]

    connectionId = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        auto_created=True,
        verbose_name=_("Connection ID"),
    )
    sender = models.ForeignKey(
        User,
        related_name="sent_connections",
        on_delete=models.CASCADE,
        verbose_name=_("Sender"),
    )
    receiver = models.ForeignKey(
        User,
        related_name="received_connections",
        on_delete=models.CASCADE,
        verbose_name=_("Receiver"),
    )
    updated = models.DateTimeField(auto_now=True, verbose_name=_("Last Updated"))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_("Creation Date"))

    # def __str__(self):
    #     return f"{self.sender.username} → {self.receiver.username}"

    def __str__(self):
        return f"Connection({self.connectionId})"

    def save(self, *args, **kwargs):
        # Prevent self-connections
        if self.sender == self.receiver:
            raise ValueError("Users cannot connect with themselves")
        super().save(*args, **kwargs)

    @property
    def most_recent_message(self):
        """Get the most recent message in this connection."""
        return self.messages.order_by("-created").first()


class Message(models.Model):
    """Represents a message sent within a connection between users."""

    class Meta:
        ordering = ["-created"]
        verbose_name = _("Message")
        verbose_name_plural = _("Messages")
        indexes = [
            models.Index(fields=["connection", "created"]),
        ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    connection = models.ForeignKey(
        Connection,
        related_name="messages",
        on_delete=models.CASCADE,
        verbose_name=_("Connection"),
    )
    user = models.ForeignKey(
        User,
        related_name="messages",
        on_delete=models.CASCADE,
        verbose_name=_("Sender"),
    )
    content = models.TextField(
        validators=[MinLengthValidator(1)], verbose_name=_("Message Text")
    )
    created = models.DateTimeField(auto_now_add=True, verbose_name=_("Creation Date"))
    auction = models.ForeignKey(
        Auction,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referenced_messages",
    )

    # def __str__(self):
    #     return f"{self.user.username}: {self.content[:30]}..."

    def __str__(self):
        return f"Message({self.id})"

    def save(self, *args, **kwargs):
        if not self.pk:
            # Update connection timestamp without full save
            Connection.objects.filter(pk=self.connectionId).update(
                updated=timezone.now()
            )
        super().save(*args, **kwargs)

    @property
    def is_sender(self, user):
        """Check if given user is the sender of this message."""
        return self.user == user
