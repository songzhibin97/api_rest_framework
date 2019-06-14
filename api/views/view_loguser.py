import uuid  # token 随机字符串
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import *
from ..tools.basedict import Basedict  # 自定义状态类


# Create your views here.
# 处理登录
class Login_view(APIView):
    """
    用于用户认证相关

    """

    def post(self, request, *args, **kwargs):
        data = Basedict()
        try:
            username = request.data.get('username')
            password = request.data.get('password')
            user = Account.objects.filter(username=username, password=password).first()
            if user:
                data.code = 1000  # 增加登录状态 code 为登录成功
                token = str(uuid.uuid4())
                data.username = username
                data.token = token
                UserAuthToken.objects.update_or_create(user_id=user.pk, defaults={'token': token})
                return Response(data.dict)
            data.code = 999  # 用户或密码错误 code 999
            data.error = '用户或密码错误'
            return Response(data.dict)
        except Exception as e:
            data.code = 800  # 出错 code 800
            data.error = e
            return Response(data.dict)
