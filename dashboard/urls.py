from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='home'),
    path('redirect/', views.redirect_user, name='redirect_user'),
    path('dashboard/admin/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/member/', views.member_dashboard, name='member_dashboard'),
    path('loans/<int:loan_id>/approve/', views.approve_loan, name='approve_loan'),
    path('loans/<int:loan_id>/reject/', views.reject_loan, name='reject_loan'),
    path('loans/apply/', views.apply_loan, name='apply_loan'),
    path('repayments/pay/', views.make_payment, name='make_payment'),
]
