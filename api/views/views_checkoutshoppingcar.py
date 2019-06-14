from django_redis import get_redis_connection
from ..tools.basedict import Basedict
from django.conf import settings
from rest_framework.response import Response
from rest_framework import viewsets
from ..auth import Auth_token
import json
import datetime
from api import models


# 判断优惠券种类的函数 create方法调用
def judgment(couponrecord):
    couponrecord_id = couponrecord.id
    coupon_coupon_type = couponrecord.coupon.coupon_type
    # 构建一个优惠券字典
    coupon_dict = {}
    coupon_dict["coupon_coupon_type"] = coupon_coupon_type
    if coupon_coupon_type == 0:  # 立减卷
        coupon_dict["money_equivalent_value"] = couponrecord.coupon.money_equivalent_value
    elif coupon_coupon_type == 1:  # 满减卷
        coupon_dict["minimum_consume"] = couponrecord.coupon.minimum_consume
        coupon_dict["money_equivalent_value"] = couponrecord.coupon.money_equivalent_value
    else:  # 折扣卷
        coupon_dict["off_percent"] = couponrecord.coupon.off_percent
    return couponrecord_id, coupon_dict


# 循环取出处理redis相应内容 list方法调用
def specialredis(self, keys):
    transfer_list = []
    for key in self.conn.scan_iter(keys):
        transfer_data = self.conn.hscan_iter(key)
        # 获取到key字符串相应的内容
        transfer_dict = {}  # 创建中转字典
        for title, content in transfer_data:  # 拆包
            title = title.decode('utf-8')  # 将拆包后的标题转化为utf-8类型
            if title == 'coupon':  # 特殊处理 需要先loads
                transfer_dict[title] = json.loads(content.decode('utf-8'))
            transfer_dict[title] = content.decode('utf-8')
        transfer_list.append(transfer_dict)
    return transfer_list


class Checkoutshoppingcar(viewsets.GenericViewSet):
    """
    结算中心
    """
    authentication_classes = [Auth_token]
    conn = get_redis_connection("default")

    def list(self, request, *args, **kwargs):
        """
        查看结算中心内容
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = Basedict()
        try:
            # 获取结算中心拼接字符串以及全局优惠券拼接字符串
            checkoutshoppingcar_key = settings.CHECKOUT_SHOPPING_CAR_KEY % (request.auth.id, '*')
            global_coupon_key = settings.GLOBAL_COUPON_KEY % (request.auth.id)
            # 循环从redis取出相应的内容
            checkoutshoppingcar_list = specialredis(self, checkoutshoppingcar_key)
            global_coupon_list = specialredis(self, global_coupon_key)
            data.data = {
                "checkoutshoppingcar_list": checkoutshoppingcar_list,
                "global_coupon_list": global_coupon_list
            }
            return Response(data.dict)
        except Exception as e:
            data.code = 2001
            data.error = '查看失败'
            return Response(data.dict)

    def create(self, request, *args, **kwargs):
        """
        将购物车的内容添加到结算中心
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        delete_redis_key = []
        delete_redis_key.append(settings.CHECKOUT_SHOPPING_CAR_KEY % (request.auth.id, "*"))
        delete_redis_key.append(settings.GLOBAL_COUPON_KEY % (request.auth.id))
        self.conn.delete(*delete_redis_key)  # 清空结算中心
        data = Basedict()
        pyment_dict = {}  # 创建结算字典
        global_coupon_dict = {
            "coupon": {},
            "default_coupon": 0
        }  # 创建全局优惠券字典
        try:
            # 获取用户从购物车添加至结算中心的课程ids
            courses_list = request.data.get("courses")
            # 循环courses_list 拼接shoppingcar_key 确认是否是从购物车中添加至结算中心
            for course in courses_list:
                key = settings.SHOPPING_CAR_KEY % (request.auth.id, course)
                if not self.conn.exists(key):
                    data.code = 1001
                    data.error = '购买商品请先添加至购物车'
                    return Response(data.dict)
                # 将购物车中的存储对应价格策略及其其他信息取出
                policy = json.loads(str(self.conn.hget(key, 'policy'), encoding='utf-8'))
                default_policy = str(self.conn.hget(key, 'default_policy'), encoding='utf-8')
                policy_info = policy[default_policy]
                # 构建存储字典
                checkout_dick = {
                    "course_id": str(course),
                    "title": str(self.conn.hget(key, 'title'), encoding='utf-8'),
                    "img": str(self.conn.hget(key, 'img'), encoding='utf-8'),
                    "policy_id": default_policy,
                    "coupon": {},
                    "default_coupon": 0
                }
                # 将购物车选中的相关的价格策略详细内容迭代添加到checkout字典中
                checkout_dick.update(policy_info)
                # 以course为键 checkout_dick为值存储至全局结算字典
                pyment_dict[str(course)] = checkout_dick
            # 获取当前时间
            time = datetime.date.today()
            # 获取当前用户可用优惠券
            couponrecord_list = models.CouponRecord.objects.filter(
                account=request.auth,
                status=0,
                coupon__valid_begin_date__lte=time,
                coupon__valid_end_date__gte=time
            )
            # 循环所有可用优惠券
            for couponrecord in couponrecord_list:
                if not couponrecord.coupon.object_id:  # 全局优惠券
                    couponrecord_id, coupon_dict = judgment(couponrecord)
                    global_coupon_dict["coupon"][couponrecord_id] = coupon_dict  # 绑定至全局优惠券内
                # 获取绑定课程id
                account_id = str(couponrecord.coupon.object_id)
                couponrecord_id, coupon_dict = judgment(couponrecord)
                # 如果该优惠券绑定的课程不在结算中心中则不做处理
                if account_id not in pyment_dict:
                    continue
                # 给结算中心有优惠券的课程绑定优惠券
                pyment_dict[account_id]["coupon"][couponrecord_id] = coupon_dict
            # 将 结算字典 以及 全局优惠券放入redis中
            # 结算字典
            for cid, cdict in pyment_dict.items():
                checkout_shopping_cay_key = settings.CHECKOUT_SHOPPING_CAR_KEY % (request.auth.id, cid)
                cdict["coupon"] = json.dumps(cdict["coupon"])
                self.conn.hmset(checkout_shopping_cay_key, cdict)
            # 全局优惠券
            global_coupon_key = settings.GLOBAL_COUPON_KEY % (request.auth.id)
            global_coupon_dict["coupon"] = json.dumps(global_coupon_dict["coupon"])
            self.conn.hmset(global_coupon_key, global_coupon_dict)
            data.data = '结算中心添加成功'
            return Response(data.dict)
        except Exception as e:
            data.code = 2000
            data.error = '添加失败'
            return Response(data.dict)

    def partial_update(self, request, *args, **kwargs):
        """
        更新结算中心的优惠券
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = Basedict()
        try:
            # 获取需要修改的优惠券是否是全局
            course_id = request.data.get("courseid")
            # 如果获取到course_id则为绑定的优惠券
            course_id = str(course_id) if course_id else course_id
            default_id = str(request.data.get("defaultid"))
            # 修改全局优惠券
            if not course_id:
                global_coupon_key = settings.GLOBAL_COUPON_KEY % (request.auth.id)
                # 传入全局优惠券为0
                if default_id == '0':
                    self.conn.hset(global_coupon_key, "default_coupon", 0)
                    data.data = "修改成功"
                    return Response(data.dict)
                load_coupon = json.loads(self.conn.hget(global_coupon_key, "coupon").decode('utf-8'))
                if default_id not in load_coupon:
                    data.code = 2002
                    data.error = '无此全站优惠券'
                    return Response(data.dict)
                self.conn.hset(global_coupon_key, "default_coupon", default_id)
                data.data = '修改成功'
                return Response(data.dict)
            # 修改绑定课程优惠券
            checkoutshoppingcar_key = settings.CHECKOUT_SHOPPING_CAR_KEY % (request.auth.id, course_id)
            if not self.conn.exists(checkoutshoppingcar_key):  # 课程不存在
                data.code = 2004
                data.error = '所选课程不存在'
                return Response(data.dict)
            if default_id == '0':
                self.conn.hset(checkoutshoppingcar_key, "default_coupon", 0)
                data.data = '修改成功'
                return Response(data.dict)
            if default_id not in json.loads(self.conn.hget(checkoutshoppingcar_key, 'coupon').decode('utf-8')):
                data.code = 2003
                data.error = '课程优惠券不存在'
                return Response(data.dict)
            self.conn.hset(checkoutshoppingcar_key, 'default_coupon', default_id)
            data.data = '修改成功'
            return Response(data.dict)

        except Exception as e:
            data.code = 3000
            data.error = "更新失败"
            return Response(data.dict)
