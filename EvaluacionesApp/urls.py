from django.urls import path
from . import views

app_name = "EvaluacionesApp"
urlpatterns = [
    path('configurar_evaluacion/<int:actividad_id>/', views.configurar_evaluacion, name='configurar_evaluacion'),
    path('procesar_evaluacion/<int:actividad_id>/<str:token_asistencia>/', views.procesar_evaluacion, name='procesar_evaluacion'),
    path('configurar_opciones/<int:pregunta_id>/', views.configurar_opciones, name="configurar_opciones"),
    path('evaluar/<int:actividad_id>/<str:token_asistencia>/', views.mostrar_evaluacion, name='responder_evaluacion'),
    path('gestionar_envio/<int:actividad_id>/', views.gestionar_evaluacion, name='gestionar_envio'),
    path('evaluacion/agradecimiento/', views.agradecimiento, name='agradecimiento'),
    path('evaluacion/dashboard_evaluacion/<int:actividad_id>/', views.dashboard_evaluacion, name='dashboard_evaluacion'),
]