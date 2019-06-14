from ..models import *
from rest_framework import viewsets
from rest_framework.response import Response
from ..serializers import course  # 引入已构的序列化组件
from ..tools.basedict import Basedict
from api import models


class Course_api(viewsets.GenericViewSet):
    """
    处理 course 视图
    """

    def list(self, request, *args, **kwargs):
        """
        所有课程接口
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = Basedict()  # 设置状态码
        try:
            queryset = Course.objects.all()  # 获取所有Course值
            bs = course.CourseSerializer(queryset, many=True)
            data.code = 1000  # 成功状态 状态码为1000
            data.data = bs.data
        except Exception as e:
            data.code = 999  # 异常状态 状态码为999
            data.error = '查询失败'  # 返回错误信息
        return Response(data.dict)

    def retrieve(self, request, *args, **kwargs):
        """
        单个课程详情查询接口

        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        data = Basedict()
        try:
            pk = int(kwargs.get('pk'))
            queryset = models.CourseDetail.objects.filter(course_id=pk)  # 某一课程详情
            bs = course.CourseDetailSerializer(queryset, many=True)
            data.code = 1000
            data.data = bs.data
        except Exception as e:
            data.code = 999
            data.error = '查询失败'
        return Response(data.dict)


class Coursecategory_api(viewsets.GenericViewSet):
    """
    课程大类
    """

    def list(self, request, *args, **kwargs):
        data = Basedict()
        try:
            queryset = models.CourseCategory.objects.all()
            bs = course.CourseCategorySerializer(queryset, many=True)
            data.code = 1000
            data.data = bs.data
        except Exception as e:
            data.code = 999
            data.error = '查询失败'
        return Response(data.dict)
#
# # Course_datails序列化组件
# class Course_datails_serialization(serializers.ModelSerializer):
#     name = serializers.CharField(source='course.name')  # 单独构建course name显示形式
#     lever = serializers.CharField(source='course.get_lever_display')  # 单独构建course lever显示形式
#     recommend_courses = serializers.SerializerMethodField()  # 单独构建recommend显示形式
#
#     class Meta:
#         model = Course_datails
#         fields = ['id', 'name', 'lever', 'slogon', 'why', 'recommend_courses']
#
#     def get_recommend_courses(self, obj):  # recommend 钩子函数
#         return [(i.id, i.name) for i in obj.recommend_courses.all()]  # 取出recommend_courses多对多关系的name
#
#
# class Course_datails_api(viewsets.ModelViewSet):
#     # serializer_class = Course_datails_serialization
#
#     def retrieve(self, request, *args, **kwargs):
#         data = {'code': None, 'data': None}
#         try:
#             pk = kwargs.get('pk')
#             queryset = Course_datails.objects.filter(course_id=pk)
#             bs = Course_datails_serialization(queryset, many=True)
#             data['code'] = 1000
#             data['data'] = bs.data
#         except Exception as e:
#             data['code'] = 999
#             data['error'] = e
#         return Response(data)
