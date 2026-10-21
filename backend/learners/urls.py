from django.urls import path

from learners import accounts, api, recovery

urlpatterns = [
    path("account/recovery/options/", recovery.options),
    path("account/<str:purpose>/request/", recovery.request_link),
    path("account/<str:purpose>/confirm/", recovery.confirm),
    path("csrf/", accounts.csrf),
    path("account/", accounts.account),
    path("account/login/", accounts.sign_in),
    path("account/logout/", accounts.sign_out),
    path("health/", api.health),
    path("pathways/", api.pathways_list),
    path("roadmaps/", api.roadmaps_list),
    path("demo/", api.demo_session),
    path("me/", api.me),
    path("dashboard/", api.dashboard),
    path("next/", api.next_step),
    path("items/", api.items_list),
    path("items/<int:item_id>/done/", api.item_done),
    path("checkpoints/<int:checkpoint_id>/<str:action>/", api.checkpoint_action),
    path("pathway/<str:action>/", api.pathway_action),
    path("opportunities/", api.opportunities_list),
]
