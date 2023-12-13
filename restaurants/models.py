from django.contrib.postgres.fields import ArrayField
from django.contrib.gis.db import models
from utils.aws import S3ImgUploader
import os


class Restaurant(models.Model):
    restaurant_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)
    category = ArrayField(models.IntegerField())
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    location = models.GeometryField(srid=4326)
    address = models.CharField()
    star_avg = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    images = ArrayField(models.URLField())
    
    is_24_hours = models.BooleanField(default=True)
    day_of_week = ArrayField(models.IntegerField())
    start_time = models.TimeField(null=True)
    end_time = models.TimeField(null=True)
    etc_reason = models.TextField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    queue = models.ManyToManyField("Reservation", through="ReservationQueue", related_name="restaurant_set", blank=True)

    class Meta:
        managed = False
        db_table = "Restaurant"
    
    def calculate_star_avg(self):
        # 해당 레스토랑의 리뷰를 기반으로 평균 별점을 계산
        avg_rating = self.review_set.aggregate(models.Avg('stars'))['stars__avg']
        return avg_rating if avg_rating is not None else 0
    
    def save_img(self, img_path):
        if os.path.exists(img_path):
            with open(img_path, "rb") as img:
                url = S3ImgUploader(img).upload_restaurant_img(self.restaurant_id)
                self.images.append(url)
                return url
        return None


# Restaurant - User 관계의 중간테이블
class Reservation(models.Model):
    reservation_id = models.AutoField(primary_key=True)
    restaurant = models.ForeignKey("Restaurant", on_delete=models.CASCADE)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, null=True, blank=True)
    phone_number = models.CharField(max_length=11, null=True, blank=True)
    reservation_date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["reservation_id"]


# Restaurant - Reservation 관계의 중간테이블
class ReservationQueue(models.Model):
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    user = models.ForeignKey("users.User", on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        unique_together = ("reservation", "restaurant")


class Manager(models.Model):
    manager_id = models.AutoField(primary_key=True)
    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "Manager"
