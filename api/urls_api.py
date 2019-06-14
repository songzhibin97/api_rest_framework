from django.conf.urls import url
from api.views.views_course import *
from api.views.views_shoping import *
from api.views.view_loguser import *  # 关于用户
from api.views.views_checkoutshoppingcar import *  # 关于结算中心
from api.views.view_goby import *  # 关于支付

urlpatterns = [
    url(r'^login/$', Login_view.as_view()),
    url(r'^course/$', Course_api.as_view({'get': 'list'})),
    url(r'^course/(?P<pk>\d+)', Course_api.as_view({'get': 'retrieve'})),
    url(r'^coursecategory/$', Coursecategory_api.as_view({'get': 'list'})),
    url(r'^shoppingcar/$',
        Shoppingcar_api.as_view({'get': 'list', 'post': 'create', 'patch': "partial_update", 'delete': 'destroy'})),
    url(r'^checkoutshoppingcar/$',
        Checkoutshoppingcar.as_view({'get': 'list', 'post': 'create', 'patch': "partial_update", })),
    url(r'^goby/$', Goby.as_view({'post': 'create'}))
]
