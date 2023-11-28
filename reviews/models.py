from django.contrib.gis.db import models
from restaurants.models import Restaurant
from users.models import User

class Review(models.Model):
    review_id = models.AutoField(primary_key=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    user = models.ForeignKey(User, models.DO_NOTHING)
    stars = models.IntegerField()
    contents = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'Review'
