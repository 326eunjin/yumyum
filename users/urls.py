from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from django.urls import path
from users.views import *

urlpatterns = [
    path('signup/', SignupView.as_view()),
    path('auth/', AuthView.as_view()),
    path('auth/verify/', TokenVerifyView.as_view()),
    path('auth/refresh/', TokenRefreshView.as_view()),
    path('mypage/', UserInfoView.as_view()),
    path('waitings/', UserWaitingView.as_view()),
    path('<int:user_id>/reviews/', UserReviewListView.as_view()),           #유저 리뷰 조회
    path('<int:user_id>/reviews/<int:review_id>', DeleteReview.as_view()),  #리뷰 삭제
]
