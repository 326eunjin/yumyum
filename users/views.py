from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenViewBase
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import authenticate
from django.db.models import F
from django.db import transaction
from datetime import datetime

from restaurants.models import Restaurant, Reservation
from .models import User
from .serializers import *
from reviews.models import Review

# Create your views here.
class SignupView(APIView):
    @transaction.atomic
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            name = serializer.validated_data['name']
            phone_number = serializer.validated_data['phone_number']
            password = serializer.validated_data['password']
            
            # 입력값 제한
            if len(name) < 1 or len(phone_number) != 11:
                return Response(
                    {
                        "status": "error",
                        "error": {
                            "code": 400,
                            "message": "Missing Required Fields",
                            "details": "Please provide values for all required fields"
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)
            # phone_number 중복 제한
            if User.objects.filter(phone_number=phone_number).exists():
                return Response(
                    {
                        "status": "error",
                        "error": {
                            "code": 409,
                            "message": "Conflict",
                            "details": "Phone number is already associated with an existing account",
                        }
                    }, status=status.HTTP_409_CONFLICT)
            # password 길이 제한
            min_password_len = 4
            if len(password) < min_password_len:
                return Response(
                    {
                        "status": "error",
                        "error": {
                            "code": 400,
                            "message": "Bad Request",
                            "details": f"Password must be at least {min_password_len} characters long",
                        }
                    }, status=status.HTTP_400_BAD_REQUEST)
            user = serializer.save()
            
            # jwt 토큰 접근
            refresh_token = TokenObtainPairSerializer.get_token(user)
            access_token = refresh_token.access_token
            res = Response(
                {
                    "status": "success",
                    "message": "User registration successful",
                    "data": {
                        "user": serializer.data,
                        "token": {
                            "access": str(access_token),
                            "refresh": str(refresh_token),
                        }
                    }
                }, status=status.HTTP_201_CREATED)
            
            # jwt 토큰 쿠키에 저장
            res.set_cookie("access", access_token, httponly=True)
            res.set_cookie("refresh", refresh_token, httponly=True)
            return res
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AuthView(APIView):
    # 로그인
    @transaction.atomic
    def post(self, request):
        # 중복 로그인 검사
        if request.user.is_authenticated:
            return Response(
                {
                    "status": "error",
                    "error": {
                        "code": 409,
                        "message": "Conflict",
                        "details": "User is already logged in"
                    }
                }, status=status.HTTP_409_CONFLICT)

        user = authenticate(request, username=request.data.get('phone_number'), password=request.data.get('password'))
        if user:
            # serializer = UserSerializer(user)
            user.last_login = datetime.now()
            user.save()
            # jwt 토큰 접근
            refresh_token = TokenObtainPairSerializer.get_token(user)
            access_token = refresh_token.access_token
            res = Response(
                {
                    "status": "success",
                    "message": "User login successful",
                    "data": {
                        "user": user.name,
                        "token": {
                            "access": str(access_token),
                            "refresh": str(refresh_token),
                        }
                    }
                }, status=status.HTTP_200_OK)
            #jwt 토큰 쿠키에 저장
            res.set_cookie("access", access_token, httponly=True)
            res.set_cookie("refresh", refresh_token, httponly=True)
            return res
    
        return Response(
            {
                "status": "error",
                "error": {
                    "code": 400,
                    "message": "Invalid Credentials",
                    "details": "The provided phone number or password is invalid",
                }
            }, status=status.HTTP_400_BAD_REQUEST)
        
    # 로그아웃
    @transaction.atomic
    def delete(self, request):
        user = request.user
        if user.is_authenticated:
            print(user)
            refresh_token = request.data.get('refresh')
            try:
                RefreshToken(refresh_token).blacklist()
                res = Response(
                    {
                        "status": "success",
                        "message": "Logout successful",
                    }, status=status.HTTP_200_OK)
                res.delete_cookie("access")
                res.delete_cookie("refresh")
                return res
            except TokenError: pass
        return Response(
            {
                "status": "error",
                "error": {
                    "code": 401,
                    "message": "Unauthorized",
                    "details": "JWT validation failed or token is expired",
                    "suggestion": "Please ensure you have a valid JWT token and try again",
                }
            }, status=status.HTTP_401_UNAUTHORIZED)


class UserInfoView(APIView):
    # 유저 조회
    def get(self, request, user_id):
        user = User.objects.filter(user_id=user_id).first()
        if not user:
            return Response({
                "status": "error",
                "error": {
                    "code": 404,
                    "message":"Not found",
                    "details": "User not found"
                }
            }, status=status.HTTP_404_NOT_FOUND) ###################################################3
        if request.user.is_authenticated and request.user == user:
            return Response({
                "status": "success",
                "message":"User information retrieved successfully",
                "user": {
                    "userid":user_id,
                    "name": user.name,
                    "phone_number": user.phone_number
                }
            }, status=status.HTTP_200_OK)
        return Response(
            {
                "status": "error",
                "error": {
                    "code": 401,
                    "message": "Unauthorized",
                    "details": "User has no authorization"
                }
            }, status=status.HTTP_401_UNAUTHORIZED)

    # 유저 삭제
    @transaction.atomic
    def delete(self, request, user_id):
        user = User.objects.filter(user_id=user_id).first()
        if not user:
            return Response({
                "status": "error",
                "error": {
                    "code": 404,
                    "message":"Not found",
                    "details": "User not found"
                }
            }, status=status.HTTP_404_NOT_FOUND)
        if user.is_authenticated:
            user.delete()
            return Response(
                {
                    "status": "success",
                    "message": "User successfully deleted"
                }, status=status.HTTP_204_NO_CONTENT)
            
        return Response(
            {
                "status": "error",
                "error": {
                    "code": 401,
                    "message": "Unauthorized",
                    "details": "Access token is missing or invalid"
                }
            }, status=status.HTTP_400_BAD_REQUEST)


class UserWaitingView(APIView):
    # 예약한 식당
    def get(self, request):
        user = request.user
        reservation_list = []
        # 회원 처리(비회원 처리는 프론트에서)
        if user.is_authenticated:
            for restaurant in user.reservations.all():
                queue = restaurant.queue
                position = queue.filter(reservation_id__lte=F('reservation_id')).count()
                reservation_list.append({
                    "restaurant_id": restaurant.restaurant_id,
                    "restaurant": restaurant.name,
                    "position": position,
                })
            return Response({
                "message": "User position retrieved successfully",
                "waitings":reservation_list
            }, status=status.HTTP_200_OK)
        return Response(
            {
                "status": "error",
                "error": {
                    "code": 401,
                    "message": "Unauthorized",
                    "details": "User not logged in or unauthorized to access this resource"
                }
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    # 예약 취소
    @transaction.atomic
    def delete(self, request):
        user = request.user
        restaurant_id = request.data.get('restaurant_id')
        restaurant = Restaurant.objects.filter(restaurant_id=restaurant_id).first()
        if not restaurant:
            return Response(
                    {
                        "status": "error",
                        "error": {
                            "code": 404,
                            "message": "Not Found",
                            "details": "Restaurant not found"
                        }
                    }, status=status.HTTP_404_NOT_FOUND)
        
        # 회원
        if user.is_authenticated:
            reservation = Reservation.objects.filter(restaurant=restaurant, user=user).first()
            if not reservation:
                return Response(
                    {
                        "status": "error",
                        "error": {
                            "code": 404,
                            "message": "Not Found",
                            "details": "Reservation not found or already canceled"
                        }
                    }, status=status.HTTP_404_NOT_FOUND)
        # 비회원
        else:
            phone_number = request.data.get('phone_number')
            if not phone_number:
                return Response({"error":"Invalid input data"}, status=status.HTTP_400_BAD_REQUEST)
            
            reservation = Reservation.objects.filter(restaurant=restaurant, phone_number=phone_number).first()
            if not reservation:
                return Response({"error":"Reservation not found"}, status=status.HTTP_404_NOT_FOUND)
        
        reservation.delete()
        return Response(
            {
                "status": "success",
                "message":"Reservation successfully canceled",
                "data": {
                    "reservation_id": reservation.reservation_id
                }
            }, status=status.HTTP_200_OK)
    
class UserReviewListView(APIView):
    def get(self, request, restaurant_id, user_id):
        user = request.user
        if user.is_authenticated:
            if restaurant_id is not None:
                restaurant = Restaurant.objects.filter(pk = restaurant_id).first() #Restaurant 가져오기
                user = User.objects.filter(user_id=user_id).first()
                if not restaurant:
                    return Response({"error":"Restaurant not found"}, status=status.HTTP_404_NOT_FOUND)
                review_infos = []
                reviews = Review.objects.filter(restaurant_id = restaurant)
                for review in reviews:
                    review_info = {
                        "review_id": review.review_id,
                        "restaurant_id" : restaurant.restaurant_id,
                        "restaurant_name" : restaurant.name,
                        "stars": review.stars,
                        "contents": review.contents,
                        "created_at": review.created_at,
                        "updated_at": review.updated_at,
                    }
                    review_infos.append(review_info)
                    
                response_data = {
                    "user_id" : user.user_id,
                    "reviews" : review_infos
                }
                return Response({"ReviewList" : response_data}, status=status.HTTP_200_OK)
            return Response({"error" : "Review not found"}, status = status.HTTP_404_NOT_FOUND)
        
class DeleteReview(APIView):
    def delete(self, request, review_id):
        user = request.user
        if user.is_authenticated:
            try:
                review = Review.objects.get(pk=review_id)
                review.delete()
                return Response({"message": "리뷰가 삭제되었습니다."}, status=status.HTTP_204_NO_CONTENT)
            except Review.DoesNotExist:
                return Response({"error": "리뷰가 없습니다."}, status=status.HTTP_404_NOT_FOUND)
        return Response({"error":"Session expired or not found"}, status=status.HTTP_400_BAD_REQUEST)
