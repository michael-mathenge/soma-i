from django.urls import path

from learners import api

urlpatterns = [
    path("health/", api.health),
    path("pathways/", api.pathways_list),
    path("demo/", api.demo_session),
    path("me/", api.me),
    path("dashboard/", api.dashboard),
    path("items/", api.items_list),
    path("items/<int:item_id>/done/", api.item_done),
    path("checkpoints/<int:checkpoint_id>/<str:action>/", api.checkpoint_action),
    path("pathway/<str:action>/", api.pathway_action),
    path("opportunities/", api.opportunities_list),
]
