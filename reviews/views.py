from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.gis.geos import Point, GEOSGeometry
from django.contrib.gis.db.models.functions import Distance
from django.contrib.gis.measure import D
from django.db.models import Q
from restaurants.models import Restaurant
from users.models import User
from .models import Review

class ReviewThread(APIView):  #thread 만들기
    def get(self, request, user_id, restaurant_id):
        restaurant = Restaurant.objects.filter(pk = restaurant_id).first() #Restaurant 가져오기
        user = User.objects.filter(user_id=user_id).first()
        user_longitude = request.GET.get('longitude')
        user_latitude = request.GET.get('latitude')

        if not (user_longitude and user_latitude):
            return Response({"error": "잘못된 요청"}, status=status.HTTP_400_BAD_REQUEST)

        user_location = Point(float(user_longitude), float(user_latitude), srid=4326)

        # 1km 반경 안에 있는 리뷰를 가져오기
        reviews = Review.objects.annotate(
            distance=Distance('restaurant__location', user_location)
        ).filter(distance__lte=D(km=1)).order_by('created_at')
        
        review_list = []
        for review in reviews:
            review_list.append({
                "review_id": review.review_id,
                "retaurant_name" : restaurant.name,
                "user_id" : user.user_id,
                "user_name" : user.name,
                "stars": review.stars,
                "menu" : review.menu,
                "contents": review.contents,
                "created_at": review.created_at,
                "updated_at": review.updated_at,
            })
        return Response({"review_list":review_list}, status=status.HTTP_200_OK)
