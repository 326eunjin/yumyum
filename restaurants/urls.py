from django.urls import path, include
from restaurants.views import *

urlpatterns = [
    path('', CreateRestaurantView.as_view()),                                 # 관리자용 식당 추가 기능
    path('<int:restaurant_id>/', RestaurantInfoView.as_view()),               # 식당 조회
    path('filtered/', RestaurantFilterView.as_view()),                        # 필터링
    path('alternative/', RestaurantAlternativeView.as_view()),                # 식당 대안 추천
    path('<int:restaurant_id>/waitings/', RestaurantWaitingView.as_view()),   # 예약
    path('manage/', RestaurantManagerView.as_view()),                         # 식당 매니저
    path('<int:restaurant_id>/manage/', RestaurantManagementView.as_view()),   # 식당 관리
    path('<int:restaurant_id>/reviews/', RestaurantReviewListView.as_view()), # 식당 리뷰 조회
    path('<int:restaurant_id>/reviews/write/', WriteReivew.as_view()),        # 리뷰 남기기
    
    path('nearby/', NearbyRestaurantInfoView.as_view()), # 테스트용
]



