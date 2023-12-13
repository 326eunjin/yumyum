from django.contrib.gis.db import models
from restaurants.models import Restaurant
from users.models import User
from django.contrib.postgres.fields import ArrayField
from utils.aws import S3ImgUploader
import os

class Review(models.Model):
    review_id = models.AutoField(primary_key=True)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    user = models.ForeignKey(User, models.DO_NOTHING)
    stars = models.IntegerField()
    contents = models.CharField(max_length=500, blank=True, null=True)
    menu = ArrayField(models.CharField(max_length=100))
    images = ArrayField(models.URLField())
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = 'Review'

    def save_img(self, img_path):
        if os.path.exists(img_path):
            with open(img_path, "rb") as img:
                url = S3ImgUploader(img).upload_review_img(self.review_id)
                self.images.append(url)
                return url
        return None