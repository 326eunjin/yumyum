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


class ReviewThread(APIView):  # thread 만들기
    def get(self, request):
        user = request.user
        if user.is_authenticated:
            user_longitude = request.GET.get("longitude")
            user_latitude = request.GET.get("latitude")

            if not (user_longitude and user_latitude):
                return Response({
                    "status": "error",
                    "error": {
                        "code": 400,
                        "message": "BadRequest",
                        "details": "Invalid parameters. Please provide valid location data."
                    }
                    }, status=status.HTTP_400_BAD_REQUEST)

            user_location = Point(float(user_longitude), float(user_latitude), srid=4326)

            # 1km 반경 안에 있는 리뷰를 가져오기
            reviews = (
                Review.objects.annotate(
                    distance=Distance("restaurant__location", user_location)
                )
                .filter(distance__lte=D(m=500))
                .order_by("created_at")
            )

            review_list = []
            for review in reviews:
                review_list.append(
                    {
                        "review_id": review.review_id,
                        "restaurant_name": review.restaurant.name,
                        "category": review.restaurant.category,
                        "user_id": review.user.user_id,
                        "user_name": review.user.name,
                        "stars": review.stars,
                        "menu": review.menu,
                        "contents": review.contents,
                        "created_at": review.created_at,
                        "updated_at": review.updated_at,
                    }
                )
            return Response({
                "status": "success",
                "message": "Nearby restauant reviews retrived sucessfully.",
                "reviews": review_list
                }, status=status.HTTP_200_OK)
            
        return Response({
                "status":"error",
                "error" : {
                    "code": 401,
                    "message": "Unathorized",
                    "details": "User not logged in or unauthorized to access this resource"
                }
            }, status = status.HTTP_401_UNAUTHORIZED)
        
