from django.urls import path

from visualization.views import DemographicsVisualizationView, ResponseIndexView, ResponsesVisualizationView, \
    ScoresVisualizationView, VisualizationIndexView

app_name = 'visualization'
urlpatterns = [
    path('', VisualizationIndexView.as_view(), name='index'),
    path('responses/', ResponseIndexView.as_view(), name='responseindex'),
    path('demographics/<int:demographic_number>', DemographicsVisualizationView.as_view(), name='demographics'),
    path('responses/<int:question_number>/<int:demographic_number>', ResponsesVisualizationView.as_view(), name='responses'),
    path('scores/<str:score_type>/<int:demographic_number>', ScoresVisualizationView.as_view(), name='scores'),

]
