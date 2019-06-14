from rest_framework.viewsets import GenericViewSet
from ..tools.basedict import Basedict
from django_redis import get_redis_connection
from rest_framework.response import Response
from api.auth import Auth_token
from django.conf import settings
import json
from api import models


class Goby(GenericViewSet):
    """
    跳转支付相关
    """
    authentication_classes = [Auth_token]

    def create(self, request, *args, **kwargs):
        """
        1. 获取用户提交数据
                {
                    balance:1000,
                    money:900
                }
           balance = request.data.get("balance")
           money = request.data.get("money")

        2. 数据验证
            - 大于等于0
            - 个人账户是否有1000贝里

            if user.auth.user.balance < balance:
                账户贝里余额不足

        优惠券ID_LIST = [1,3,4]
        总价
        实际支付
        3. 去结算中获取课程信息
            for course_dict in redis的结算中获取：
                # 获取课程ID
                # 根据course_id去数据库检查状态

                # 获取价格策略
                # 根据policy_id去数据库检查是否还依然存在

                # 获取使用优惠券ID
                # 根据优惠券ID检查优惠券是否过期

                # 获取原价+获取优惠券类型
                    - 立减
                        0 = 获取原价 - 优惠券金额
                        或
                        折后价格 = 获取原价 - 优惠券金额
                    - 满减：是否满足限制
                        折后价格 = 获取原价 - 优惠券金额
                    - 折扣：
                        折后价格 = 获取原价 * 80 / 100

        4. 全站优惠券
            - 去数据库校验全站优惠券的合法性
            - 应用优惠券：
                - 立减
                    0 = 实际支付 - 优惠券金额
                    或
                    折后价格 =实际支付 - 优惠券金额
                - 满减：是否满足限制
                    折后价格 = 实际支付 - 优惠券金额
                - 折扣：
                    折后价格 = 实际支付 * 80 / 100
            - 实际支付
        5. 贝里抵扣

        6. 总金额校验
            实际支付 - 贝里 = money:900

        7. 为当前课程生成订单

                - 订单表创建一条数据 Order
                    - 订单详细表创建一条数据 OrderDetail   EnrolledCourse
                    - 订单详细表创建一条数据 OrderDetail   EnrolledCourse
                    - 订单详细表创建一条数据 OrderDetail   EnrolledCourse

                - 如果有贝里支付
                    - 贝里金额扣除  Account
                    - 交易记录     TransactionRecord

                - 优惠券状态更新   CouponRecord

                注意：
                    如果支付宝支付金额0，  表示订单状态：已支付
                    如果支付宝支付金额110，表示订单状态：未支付
                        - 生成URL（含订单号）
                        - 回调函数：更新订单状态

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = Basedict()
        conn = get_redis_connection('default')
        count_price = 0
        try:
            # 创建事务
            pipe = conn.pipeline(transaction=True)
            # 获取用户提交数据
            bailey_money = request.data.get("bailey")
            money = request.data.get("money")
            # 判断前端提交数据类型或数值是否合法
            if not int(bailey_money) > 0 and int(money) > 0:
                data.code = 2002
                data.error = '提交金额有误'
                return Response(data.dict)
            # 判断用户账户贝里币是否足够支付
            if not request.auth.balance >= int(bailey_money):
                data.code = 2003
                data.error = '贝里币不足'
                return Response(data.dict)
            # 创建绑定课程优惠券列表
            coupon_list = []
            # 创建全站优惠券列表
            global_coupon_list = []
            # 从结算中心获取课程信息
            # 获取全局以及绑定课程拼接字符串
            checkoutshoppingcar_key = settings.CHECKOUT_SHOPPING_CAR_KEY % (request.auth.id, '*')
            global_coupon_key = settings.GLOBAL_COUPON_KEY % (request.auth.id)
            checkoutshoppingcar_data = conn.scan_iter(checkoutshoppingcar_key)
            global_coupon_data = conn.scan_iter(global_coupon_key)
            for item in checkoutshoppingcar_data:
                # 构建绑定课程优惠券信息字典
                checkoutshoppingcar_dict = {}
                checkoutshoppingcar_dict[conn.hget(item, "course_id").decode('utf-8')] = {
                    "price": conn.hget(item, "price").decode('utf-8'),
                    "policy_id": conn.hget(item, "policy_id").decode("utf-8"),
                    "coupon": json.loads(conn.hget(item, "coupon").decode('utf-8')),
                    "default_coupon": conn.hget(item, "default_coupon").decode('utf-8')
                }
                coupon_list.append(checkoutshoppingcar_dict)
            for item in global_coupon_data:
                global_coupon_dict = {
                    "default_coupon": conn.hget(item, 'default_coupon').decode('utf-8'),
                    "coupon": json.loads(conn.hget(item, "coupon").decode('utf-8'))
                }
                global_coupon_list.append(global_coupon_dict)
            # 判断课程状态
            for course in coupon_list:
                for course_id, countent in course.items():
                    ret = models.Course.objects.filter(pk=int(course_id))
                    if not ret:
                        data.code = 2004
                        data.error = '课程信息已过期'
                        return Response(data.dict)
                    policy_id = countent.get("policy_id")
                    # 判断价格策略是否合法有效
                    policy = models.PricePolicy.objects.filter(pk=int(policy_id))
                    if not policy:
                        data.code = 2005
                        data.error = "价格策略无效"
                        return Response(data.dict)
                    # 获取绑定课程优惠券id 检验优惠券是否有效
                    coupon_ids_obj = countent.get("coupon")  # 获取到当前课程可用优惠券
                    for coupon_id in coupon_ids_obj:
                        obj = models.CouponRecord.objects.filter(pk=int(coupon_id)).first()
                        if not obj.status == 0:
                            data.code = 2006
                            data.error = '绑定优惠券已失效'
                            return Response(data.dict)
                    # 通过校验 计算绑定课程价格
                    default_coupon = countent.get("default_coupon")
                    if int(default_coupon) == 0:
                        course_price = float(countent.get("price"))
                        count_price += course_price
                    else:
                        # 获取优惠券类别
                        choice_count_type = coupon_ids_obj.get(default_coupon).get("coupon_coupon_type")
                        if int(choice_count_type) == 0:
                            # 处理通用卷
                            coupon_price = float(coupon_ids_obj.get(default_coupon).get("money_equivalent_value"))
                            course_price = float(countent.get("price")) - coupon_price
                            if course_price > 0:
                                count_price += course_price
                            else:
                                course_price = 0
                        elif int(choice_count_type) == 1:
                            # 处理满减卷
                            minimum = float(coupon_ids_obj.get(default_coupon).get("minimum_consume"))
                            coupon_price = float(coupon_ids_obj.get(default_coupon).get("money_equivalent_value"))
                            course_price = float(countent.get("price"))
                            if course_price >= minimum:
                                course_price -= coupon_price
                            count_price += course_price
                        elif int(choice_count_type) == 2:
                            # 处理折扣卷
                            off_percent = float(coupon_ids_obj.get(default_coupon).get("off_percent")) / 100
                            course_price = float(countent.get("price")) * off_percent
                            count_price += course_price
            # 获取全站优惠券id 检验优惠券是否有效
            for global_coupon in global_coupon_list:
                global_coupon_obj = global_coupon.get("coupon")
                for global_coupon_id in global_coupon_obj:
                    obj = models.CouponRecord.objects.filter(pk=int(global_coupon_id)).first()
                    if not obj.status == 0:
                        data.code = 2007
                        data.error = "全站优惠券已失效"
                        return Response(data.dict)
                global_default_coupon = global_coupon.get("default_coupon")
                if int(global_default_coupon) == 0:
                    pass
                else:
                    # 获取优惠券类型
                    global_coupon_count_type = global_coupon_obj.get(global_default_coupon).get("coupon_coupon_type")
                    if int(global_coupon_count_type) == 0:
                        # 处理通用卷
                        global_coupon_price = float(
                            global_coupon_obj.get(global_default_coupon).get("money_equivalent_value"))
                        if count_price > global_coupon_price:
                            count_price -= global_coupon_price
                        else:
                            count_price = 0
                    elif int(global_coupon_count_type) == 1:
                        # 处理满减卷
                        global_minimum = float(global_coupon_obj.get(global_default_coupon).get("minimum_consume"))
                        global_coupon_price = float(
                            global_coupon_obj.get(global_default_coupon).get("money_equivalent_value"))
                        if count_price >= global_minimum:
                            count_price -= global_coupon_price
                    elif int(global_coupon_count_type) == 2:
                        # 处理折扣卷
                        global_off_percent = float(
                            global_coupon_obj.get(global_default_coupon).get("off_percent")) / 100
                        count_price = count_price * global_off_percent
            # 扣减贝里
            count_price -= float(bailey_money)
            if count_price <= 0:
                count_price = 0
            data.data = "实际付款%s" % count_price
            """
            金额 物品内容跳转支付宝支付即可
            """
            return Response(data.dict)
        except Exception as e:
            print(e)
            return Response("...")
