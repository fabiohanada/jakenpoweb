from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('criar-sala/', views.criar_sala, name='criar_sala'),
    path('sala/<int:sala_id>/', views.entrar_sala, name='entrar_sala'),
    path('sala/<int:sala_id>/jogar/', views.fazer_jogada, name='fazer_jogada'),
    path('sala/<int:sala_id>/jogar-novamente/', views.jogar_novamente, name='jogar_novamente'),
    path('sala/<int:sala_id>/sair/', views.sair_sala, name='sair_sala'), # <-- ADICIONE ESTA LINHA
    path('registrar/', views.registrar, name='registrar'),
    path('login/', views.entrar, name='login'),
    path('logout/', LogoutView.as_view(next_page='login'), name='logout'),
    path('sala/<int:sala_id>/api/', views.status_sala_api, name='status_sala_api'),
    path('criar-sala-computador/', views.criar_sala_computador, name='criar_sala_computador'),
]