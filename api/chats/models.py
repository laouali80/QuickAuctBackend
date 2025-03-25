from django.db import models
import uuid
from api.users.models import User
# Create your models here.

class Connection(models.Model):
   sender = models.ForeignKey(
      User,
      related_name='sent_connections',
      on_delete=models.CASCADE
   )
   receiver= models.ForeignKey(
      User,
      related_name='received_connections',
      on_delete=models.CASCADE
   )
   updated = models.DateTimeField(auto_now=True)
   created = models.DateTimeField(auto_now_add=True)

   def __str__(self):
      return self.sender.username + ' --> ' + self.receiver.username