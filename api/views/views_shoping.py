from django_redis import get_redis_connection
from api import models
from django.conf import settings
from ..tools.basedict import Basedict  # 封装的BASE dictionary
from ..tools.exception import PricePolicyInvalid
from rest_framework import viewsets
from ..auth import Auth_token
import json
from rest_framework.response import Response
from django.core.exceptions import ObjectDoesNotExist


class Shoppingcar_api(viewsets.GenericViewSet):
    authentication_classes = [Auth_token, ]
    conn = get_redis_connection("default")  # 全局连接池

    def list(self, request, *args, **kwargs):
        """
        查看购物车的商品
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = Basedict()
        try:
            redis_str = settings.SHOPPING_CAR_KEY % (request.auth.id, "*")  # 获取存储在redis中shoppingcar字符串格式
            course_list = []  # 创建课程列表
            for key in self.conn.scan_iter(redis_str, count=10):  # 遍历当前用于购物车内容 构建字典机构返回list
                info = {
                    "title": self.conn.hget(key, 'title').decode('utf-8'),
                    "img": self.conn.hget(key, 'img').decode('utf-8'),
                    "policy": json.loads(self.conn.hget(key, 'policy').decode('utf-8')),
                    "default_policy": self.conn.hget(key, 'default_policy').decode('utf-8')
                }
                course_list.append(info)
            data.data = course_list
        except Exception as e:
            data.code = 1002
            print(e)
            data.error = '查询失败'
        return Response(data.dict)

    def create(self, request, *args, **kwargs):
        """
        添加商品至购物车

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = Basedict()
        try:
            # 获取用户提交的课程ID以及价格策略ID
            course_id = int(request.data.get("courseid"))
            policy_id = int(request.data.get("policyid"))
            # 获取课程信息
            course = models.Course.objects.get(id=course_id)

            # 获取该课程的相关价格策略
            price_policy_list = course.price_policy.all()
            price_policy_dict = {}  # 构建字典
            for iter in price_policy_list:
                price_policy_dict[int(iter.id)] = {
                    "period": iter.valid_period,
                    "period_display": iter.get_valid_period_display(),
                    "price": iter.price,
                }
            # 判断用户提交的价格策略是否合法
            if policy_id not in price_policy_dict:
                # 不合法用户
                raise PricePolicyInvalid("价格策略不合法")
            # 将购物信息添加到redis中
            redis_str = settings.SHOPPING_CAR_KEY % (request.auth.id, course_id)
            car_dict = {
                "title": course.name,
                "img": course.course_img,
                "default_policy": policy_id,
                "policy": json.dumps(price_policy_dict)
            }  # 构建存储字典
            self.conn.hmset(redis_str, car_dict)
            data.data = '添加成功'

        except PricePolicyInvalid as e:
            data.code = 2001
            data.error = '价格策略不合法'
        except ObjectDoesNotExist as e:
            data.code = 2002
            data.error = '商品信息无效'
        except Exception as e:
            data.code = 2003
            data.error = '添加失败'
        return Response(data.dict)

    def partial_update(self, request, *args, **kwargs):
        """
        更新价格策略
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = Basedict()
        try:
            # 获取价格策略ID以及课程ID
            course_id = int(request.data.get('courseid'))
            policy_id = str(request.data.get('policyid'))

            # 检测key是否存在redis的key中
            redis_str = settings.SHOPPING_CAR_KEY % (request.auth.id, course_id)
            if not self.conn.exists(redis_str):
                data.code = 2003
                data.error = '购物车中不存在此课程'
                return Response(data.dict)
            # 获取redis存储的价格策略
            policy_dict = json.loads(str(self.conn.hget(redis_str, 'policy'), encoding='utf-8'))
            if policy_id not in policy_dict:  # 如果传来的policy_id不在policy_dict
                data.code = 2004
                data.error = '价格策略不合法'
                return Response(data.dict)
            # 在购物车中修改该课程的默认价格
            self.conn.hset(redis_str, 'default_policy', policy_id)
            data.data = '修改成功'
            return Response(data.dict)
        except Exception as e:
            data.code = 2005
            data.error = '更新失败'
            return Response(data.dict)

    def destroy(self, request, *args, **kwargs):
        """
        删除购物车课程
        :param self:
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = Basedict()
        try:
            courses_id_list = request.data.get("courseids")
            redis_list = [settings.SHOPPING_CAR_KEY % (request.auth.id, course_id) for course_id in courses_id_list]
            self.conn.delete(*redis_list)
        except Exception as e:
            print(e)
            data.code = 1002
            data.error = '删除失败'
        return Response(data.dict)
