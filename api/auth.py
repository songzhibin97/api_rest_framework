from rest_framework.authentication import BaseAuthentication
from .models import *
from rest_framework import exceptions
from rest_framework.response import Response


class Auth_token(BaseAuthentication):
    def authenticate(self, request, *args, **kwargs):
        try:
            token = request.query_params.get('token')  # request.query_params.get相当于request._request.get
            auth_pass = UserAuthToken.objects.filter(token=token).first()
            if auth_pass:  # 通过校验
                return auth_pass.user.username, auth_pass.user
            raise exceptions.AuthenticationFailed('验证失败')
        except Exception as e:
            return None
