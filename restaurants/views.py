from geopy.distance import distance
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.gis.geos import Point, GEOSGeometry
from django.contrib.gis.measure import D
from django.db.models import Q, Avg
from django.db import transaction
from datetime import datetime

from .serializers import RestaurantSerializer, OperatingHourSerializer
from .models import Restaurant, Reservation
from reviews.models import Review
from config import settings

# Create your views here.
class CreateRestaurantView(APIView):
    @transaction.atomic
    def post(self, request):
        if request.user.is_admin:
            longitude = request.data.get("longitude")
            latitude = request.data.get("latitude")
            try:
                longitude = float(longitude)
                latitude = float(latitude)
            except ValueError:
                return Response({"error": "Invalid input data"}, status=status.HTTP_400_BAD_REQUEST)

            location = GEOSGeometry(f"POINT({longitude} {latitude})", srid=4326)
            request.data["location"] = location
            serializer = RestaurantSerializer(data=request.data)
            if serializer.is_valid():
                restaurant = serializer.save()
                return Response(
                    {
                        "status": "success",
                        "message": "Restaurant successfully added",
                        "data": {
                            "restaurant_id": restaurant.restaurant_id,
                            "name": restaurant.name,
                            "category": restaurant.category,
                            "longitude": restaurant.longitude,
                            "latitude": restaurant.latitude,
                            "address": restaurant.address,
                            "created_at": restaurant.created_at,
                            "updated_at": restaurant.updated_at,
                        }
                    }, status=status.HTTP_201_CREATED,)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error": "Unauthorized access"}, status=status.HTTP_401_UNAUTHORIZED)

class RestaurantInfoView(APIView):
    def get(self, request, restaurant_id):
        restaurant = Restaurant.objects.filter(restaurant_id=restaurant_id).first()
        if not restaurant:
            return Response({
                "status": "error",
                "error": {
                    "code": 404,
                    "message": "Not Found",
                    "details": f"Restaurant with ID {restaurant_id} not found."
                }
            }, status=status.HTTP_404_NOT_FOUND)
            
        review1, review2 = Review.objects.order_by('-created_at')[:2]
        return Response({
            "status": "success",
            "message": "Restaurant information retrieved successfully",
            "data": {
                "restaurant_id": restaurant_id,
                "name": restaurant.name,
                "star_avg" : restaurant.star_avg,
                "category": restaurant.category,
                "longitude": restaurant.longitude,
                "latitude": restaurant.latitude,
                "address": restaurant.address,
                "waiting": restaurant.user_set.count(),
                "image": restaurant.image,
                "is_24_hours": restaurant.is_24_hours,
                "day_of_week": restaurant.day_of_week,
                "start_time": str(restaurant.start_time.strftime("%H:%M")) if restaurant.start_time else "00:00",
                "end_time": str(restaurant.end_time.strftime("%H:%M")) if restaurant.end_time else "00:00",
                "etc_reason": restaurant.etc_reason,
                "created_at": restaurant.created_at,
                "updated_at": restaurant.updated_at,
                "review1": {
                    "user_name": review1.user.name,
                    "stars": review1.stars,
                    "contents": review1.contents,
                },
                "review2": {
                    "user_name": review2.user.name,
                    "stars": review2.stars,
                    "contents": review2.contents,
                }
            }
        }, status=status.HTTP_200_OK)


class RestaurantFilterView(APIView):
    def get(self, request):
        user_restaurant_name = request.GET.get('restaurant_name', "")
        user_category = request.GET.get('category', [])
        user_longitude = request.GET.get('longitude')
        user_latitude = request.GET.get('latitude')
        if not (user_longitude and user_latitude):
            return Response({"error": "Invalid request. Please check your input data"}, status=status.HTTP_400_BAD_REQUEST)
        user_location = Point((float(user_longitude), float(user_latitude)), srid=4326)

        # 요청에 해당하는 query 작성
        now = datetime.now()
        query = Q(name__contains=user_restaurant_name)                 # 이름 검색
        query &= (Q(is_24_hours=True) | Q(start_time__lte=now, end_time__gte=now)) # 운영시간 확인
        query &= Q(location__distance_lte=(user_location, D(km=0.1)))   # 반경 100m
        if user_category:
            for category_id in user_category.split(','):
                query &= Q(category__contains=[category_id])
        
        restaurant_ids = []
        restaurants = Restaurant.objects.filter(query)
        print(restaurants.count())
        for restaurant in restaurants:
            restaurant_ids.append(restaurant.restaurant_id)
        restaurant_ids.sort(key=lambda x : Restaurant.objects.get(pk=x).star_avg)
        return Response({
            "status": "success",
            "message": "Nearby restaurants retrieved successfully",
            "restaurants": restaurant_ids,
        },status=status.HTTP_200_OK)

class RestaurantAlternativeView(APIView):
    def get(self, request):
        restaurant_id = request.GET.get('restaurant_id')
        restaurant = Restaurant.objects.filter(restaurant_id=restaurant_id).first()
        if not restaurant:
            return Response({
                "status": "error",
                "error": {
                    "code": 404,
                    "message": "Not Found",
                    "details": "Restaurant not found",
                }
            }, status=status.HTTP_404_NOT_FOUND)
        
        latitude = restaurant.latitude
        longitude = restaurant.longitude
        location = Point(float(longitude), float(latitude), srid=4326)
        categories = restaurant.category
        
        now = datetime.now()
        query = Q(location__distance_lte=(location,D(km=1)))
        query = ~Q(restaurant_id=restaurant_id)
        query &= (Q(is_24_hours=True) | Q(start_time__lte=now, end_time__gte=now)) # 운영시간 확인
        for category_id in categories:
            query &= Q(category__contains=[category_id])
            
        restaurant_list = []
        restaurants = Restaurant.objects.filter(query)
        for alter_restaurant in restaurants:
            point1 = (float(latitude), float(longitude))
            point2 = (float(alter_restaurant.latitude), float(alter_restaurant.longitude))
            dist = distance(point1, point2).meters
            
            restaurant_list.append({
                "restaurant_id": alter_restaurant.restaurant_id,
                "name": alter_restaurant.name,
                "category": alter_restaurant.category,
                "is_24_hours": alter_restaurant.is_24_hours,
                "day_of_week": alter_restaurant.day_of_week,
                "start_time": str(alter_restaurant.start_time.strftime("%H:%M")) if alter_restaurant.start_time else "00:00",
                "end_time": str(alter_restaurant.end_time.strftime("%H:%M"))if alter_restaurant.end_time else "00:00",
                "etc_reason": alter_restaurant.etc_reason,
                "distance": f'{dist:.2f}m'
            })
        restaurant_list.sort(key=lambda x:float(x['distance'][:-2]))
        return Response({
            "status": "success",
            "message": "Nearby restaurants retrieved successfully",
            "data": restaurant_list
        }, status=status.HTTP_200_OK)

class RestaurantWaitingView(APIView):
    # 식당 웨이팅 조회(유저)
    def get(self, request, restaurant_id):
        restaurant = Restaurant.objects.filter(restaurant_id=restaurant_id).first()
        if not restaurant:
            return Response({"error": "Restaurant not found"}, status=status.HTTP_400_BAD_REQUEST)
        
        waiting_list = []
        for waiting in restaurant.queue.all():
            user = waiting.user
            waiting_list.append({
                "reservation_id":waiting.reservation_id,
                "restaurant":waiting.restaurant.name,
                "user":user.name if user else 'Anonymous user',
                "phone_number":waiting.phone_number})
        return Response({
            "message":"Restaurant waiting retrieved successfully",
            "waitings": waiting_list,
            }, status=status.HTTP_200_OK)

    # 예약 등록(유저)
    @transaction.atomic
    def post(self, request, restaurant_id):
        user = request.user
        restaurant = Restaurant.objects.filter(restaurant_id=restaurant_id).first()
        if not restaurant:
            return Response({"error": "Restaurant not found"}, status=status.HTTP_404_NOT_FOUND)

        # 회원 처리
        if user.is_authenticated:
            if restaurant.queue.filter(user=user).exists():
                return Response({"error":"Waiting already exists"}, status=status.HTTP_409_CONFLICT)
            new_reservation = Reservation.objects.create(restaurant=restaurant, user=user, phone_number=user.phone_number)
            restaurant.queue.add(new_reservation)
        # 비회원 처리
        else:
            phone_number = request.data.get('phone_number')
            if not phone_number:
                return Response({"error": "Invalid input data"}, status=status.HTTP_400_BAD_REQUEST)
            if restaurant.queue.filter(phone_number=phone_number).exists():
                return Response({"error":"Waiting already exists"}, status=status.HTTP_409_CONFLICT)
            new_reservation = Reservation.objects.create(restaurant=restaurant, phone_number=phone_number)
            restaurant.queue.add(new_reservation)

        restaurant.save()
        position = len(restaurant.queue.all())
        return Response({
            "status": "success",
            "message": "Joined the queue successfully.",
            "position": position
        }, status=status.HTTP_200_OK)

    # 예약 입장(매니저)
    @transaction.atomic
    def patch(self, request, restaurant_id):
        restaurant = Restaurant.objects.filter(restaurant_id=restaurant_id).first()
        if not restaurant:
            return Response({"error": "Restaurant not found"}, status=status.HTTP_404_NOT_FOUND)
        
        queue = restaurant.queue
        if not queue.exists():
            return Response({"error": "Waiting does not exist"}, status=status.HTTP_400_BAD_REQUEST)
       
        next = queue.first()
        queue.remove(next)
        restaurant.save()

        if next.user:
            next_name = next.user.name
            next.user.reservations.remove(restaurant)
        else:
            next_name = 'Anonymous user'
        return Response({
            "message": "Queuing successful",
            "name":next_name,
            "phone_number":next.phone_number,
            }, status=status.HTTP_200_OK)

class RestaurantManagerView(APIView):
    # 매니저 추가
    def post(self, request):
        pass

class RestaurantManagementView(APIView):
    # 식당 사진 삽입
    def post(self, request, restaurant_id):
        img_path = request.data.get('img_path')
        if not img_path:
            return Response({
                "status": "error",
                "error": {
                    "code": 400,
                    "message": "Bad Request",
                    "details": "Invalid image path",
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
        restaurant = Restaurant.objects.filter(restaurant_id = restaurant_id).first()
        if not restaurant:
            return Response({
                "status": "error",
                "error": {
                    "code": 404,
                    "message": "Not Found",
                    "details": "Restaurant not found",
                }
            }, status=status.HTTP_404_NOT_FOUND)
        url = restaurant.save_img(img_path)
        return Response({
            "status": "success",
            "message": "Save successful",
            "base_url": settings.S3_base_url,
            "url": url,
        }, status=status.HTTP_200_OK)
    
    # 식당 정보 변경
    @transaction.atomic
    def put(self, request, restaurant_id):
        user = request.user
        serializer = OperatingHourSerializer(data=request.data)
        if serializer.is_valid():
            restaurant = Restaurant.objects.filter(restaurant_id=restaurant_id).first()
            if not user.is_staff: # 매니저 존재시 매니저 여부로 확인
                return Response({"error":"Unauthorized access"}, status=status.HTTP_403_FORBIDDEN)
            if not restaurant:
                return Response({"error":"Restaurant not found"}, status=status.HTTP_404_NOT_FOUND)
            
            is_24_hours = serializer.validated_data.get('is_24_hours')
            day_of_week = serializer.validated_data.get('day_of_week')
            start_time = serializer.validated_data.get('start_time')
            end_time = serializer.validated_data.get('end_time')
            etc_reason = serializer.validated_data.get('etc_reason')
            
            restaurant.is_24_hours = is_24_hours
            restaurant.day_of_week = day_of_week
            restaurant.start_time = start_time
            restaurant.end_time = end_time
            restaurant.etc_reason = etc_reason
            restaurant.save()
            return Response({
                "status": "success",
                "message":"Update restaurant operating hour successful",
                "is_24_hours": restaurant.is_24_hours,
                "day_of_week": restaurant.day_of_week,
                "start_time": restaurant.start_time,
                "end_time": restaurant.end_time,
                "etc_reason": restaurant.etc_reason
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RestaurantReviewListView(APIView):
    def get(self, request, restaurant_id):
        user = request.user
        if user.is_authenticated:
            if restaurant_id is not None:
                restaurant = Restaurant.objects.filter(pk = restaurant_id).first() #Restaurant 가져오기
                if not restaurant:
                    return Response({"error":"Restaurant not found"}, status=status.HTTP_404_NOT_FOUND)
                review_infos = []
                reviews = Review.objects.filter(restaurant_id = restaurant)
                for review in reviews:
                    review_info = {
                        "review_id": review.review_id,
                        "stars": review.stars,
                        "user_id" : user.user_id,
                        "use_name" : user.name,
                        "menu" : review.menu,
                        "contents": review.contents,
                        "created_at": review.created_at,
                        "updated_at": review.updated_at,
                    }
                    review_infos.append(review_info)
                    
                responst_data = {
                    "restaurant_id" : restaurant.restaurant_id,
                    "restaurant_name" : restaurant.name,
                    "reviews" : review_infos
                }
                return Response(responst_data, status=status.HTTP_200_OK)
            error_response = {
                    "status":"error",
                    "error" : {
                        "code": 400,
                        "message": "Not Found",
                        "details": "Restaurant with ID 123 not found"
                    }
                }
            return Response(error_response, status = status.HTTP_404_NOT_FOUND)
        error_response2 = {
                    "status":"error",
                    "error" : {
                        "code": 500,
                        "message": "Internal Server error",
                        "details": "An unexpected error occurred while processing your request."
                    }
                }
        return Response(error_response2, status = status.HTTP_404_NOT_FOUND)

class WriteReivew(APIView):   
    permission_classes=[AllowAny]
    @transaction.atomic
    def post(self, request, restaurant_id):
        user = request.user
        if user.is_authenticated:
            name = request.data.get('name')
            stars = request.data.get('stars')
            menu = request.data.get('menu')
            contents = request.data.get('contents')
            if not (name,stars,menu,contents):
                return Response({"error": "평점과 리뷰 내용이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)
            try:
                restaurant = Restaurant.objects.get(restaurant_id=restaurant_id)
            except Restaurant.DoesNotExist:
                return Response({"error": "레스토랑을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
            review, created = Review.objects.get_or_create(restaurant=restaurant, user=user, stars=stars, menu=menu, contents=contents)
            star_avg = Review.objects.filter(restaurant=restaurant).aggregate(Avg('stars'))['stars__avg']
            restaurant.star_avg = star_avg
            restaurant.save()
            if created:

                response_data = {
                    "status": "success",
                    "message": "Review submitted successfully",
                    "data": {
                        "restaurant_id": restaurant.restaurant_id,
                        "restaurant_name": restaurant.name,
                        "review_id": review.review_id,
                        "user_id": user.user_id,
                        "stars": review.stars,
                        "menu": review.menu,
                        "contents": review.contents,
                    #    "images" : review.images,
                        "created_at": review.created_at,
                        "updated_at": review.updated_at
                    }
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                error_response = {
                    "status":"error",
                    "error" : {
                        "code": 400,
                        "message": "Bad request",
                        "details": "Failed to submit restaurant review. Please check your input and try again."
                    }
                }
                return Response(error_response, status=status.HTTP_400_BAD_REQUEST)
        return Response({"error : 세션 만료"}, status=status.HTTP_400_BAD_REQUEST)

class EditReview(APIView):
    @transaction.atomic
    def put(self, request, restaurant_id, review_id):    #리뷰 수정 코드
        user = request.user
        if user.is_authenticated:
            name = request.data.get('name')
            stars = request.data.get('stars')
            menu = request.data.get('menu')
            contents = request.data.get('contents')

            if not (name, stars, menu, contents):
                return Response({"error": "평점과 리뷰 내용이 없습니다."}, status=status.HTTP_400_BAD_REQUEST)

            try:
                restaurant = Restaurant.objects.get(restaurant_id=restaurant_id)
                review = Review.objects.get(restaurant=restaurant, user=user, review_id=review_id)
            except Restaurant.DoesNotExist:
                return Response({"error": "레스토랑을 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)
            except Review.DoesNotExist:
                return Response({"error": "리뷰를 찾을 수 없습니다."}, status=status.HTTP_404_NOT_FOUND)

            # 새로운 데이터로 리뷰 업데이트
            review.stars = stars
            review.menu = menu
            review.contents = contents
            review.save()

            # 레스토랑의 평균 평점 업데이트
            star_avg = Review.objects.filter(restaurant=restaurant).aggregate(Avg('stars'))['stars__avg']
            restaurant.star_avg = star_avg
            restaurant.save()

            response_data = {
                "status": "success",
                "message": "리뷰가 성공적으로 업데이트되었습니다.",
                "data": {
                    "restaurant_id": restaurant.restaurant_id,
                    "restaurant_name": restaurant.name,
                    "review_id": review.review_id,
                    "user_id": user.user_id,
                    "stars": review.stars,
                    "menu": review.menu,
                    "contents": review.contents,
                    "images": review.images,
                    "created_at": review.created_at,
                    "updated_at": review.updated_at
                }
            }
            return Response(response_data, status=status.HTTP_200_OK)

        return Response({"error": "세션 만료"}, status=status.HTTP_400_BAD_REQUEST)
    

class NearbyRestaurantInfoView(APIView):
    def get(self, request):
        latitude = request.GET.get('latitude')
        longitude = request.GET.get('longitude')
        dist = request.GET.get('dist')
        try:
            latitude = float(latitude)
            longitude = float(longitude)
            dist = float(dist) if dist else 0.5
        except Exception:
            return Response({
                "status": "error",
                "error": {
                    "code": 400,
                    "message": "Bad Request",
                    "details": "Invalid input data",
                },
            }, status=status.HTTP_400_BAD_REQUEST)
        
        now = datetime.now()
        user_location = Point((longitude, latitude), srid=4326)
        query = Q(location__distance_lte=(user_location, D(km=dist)))
        query &= (Q(is_24_hours=True) | Q(start_time__lte=now, end_time__gte=now)) # 운영시간 확인
        restaurants = Restaurant.objects.filter(query)
        
        restaurant_list = []
        for restaurant in restaurants:
            restaurant_list.append({
                "restaurant_id":restaurant.restaurant_id,
                "category":restaurant.category,
                "latitude":restaurant.latitude,
                "longitude":restaurant.longitude,
            })
        return Response({
            "status":"success",
            "message":"All restaurants retrieved successfully",
            "restaurants":restaurant_list,
        }, status=status.HTTP_200_OK)

class AllRestaurantInfoView(APIView):
    def get(self, request):
        category = int(request.GET.get('category'))
        
        restaurant_location_list = []
        for restaurant in Restaurant.objects.all():
            if category in restaurant.category:
                restaurant_location_list.append({
                    "restaurant_id": restaurant.restaurant_id,
                    "lat": restaurant.latitude,
                    "lng": restaurant.longitude,
                })
        return Response({
            "status":"success",
            "message":"All restaurants retrieved successfully",
            "restaurants":restaurant_location_list,
        }, status=status.HTTP_200_OK)
