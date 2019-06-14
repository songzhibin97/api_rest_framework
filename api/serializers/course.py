"""
序列化组件

"""
from api import models
from rest_framework import serializers


class CourseSerializer(serializers.ModelSerializer):
    """
    专题课 or 学位课模块 序列化组件
    """
    course_type = serializers.CharField(source='get_course_type_display')
    status = serializers.CharField(source='get_status_display')
    level = serializers.CharField(source='get_level_display')

    class Meta:
        model = models.Course
        fields = ['id', 'name', 'course_type', 'level', 'course_img', 'status', 'brief', 'pub_date', 'period', ]


class CourseCategorySerializer(serializers.ModelSerializer):
    """
    课程类序列化组件
    """

    class Meta:
        model = models.CourseCategory
        fields = '__all__'


class CourseDetailSerializer(serializers.ModelSerializer):
    """
    学位课序列化组件
    """
    #     # one2one/fk/choice
    name = serializers.CharField(source='course.name')
    img = serializers.CharField(source='course.course_img')
    level = serializers.CharField(source='course.get_level_display')

    #     m2m
    recommend_courses = serializers.SerializerMethodField()
    teachers = serializers.SerializerMethodField()
    coursechapter = serializers.SerializerMethodField()

    #
    class Meta:
        model = models.CourseDetail
        fields = ['id', 'hours', 'course_slogan', 'video_brief_link', 'why_study', 'what_to_study_brief',
                  'career_improvement', 'prerequisite', 'name', 'level', 'img', 'recommend_courses', 'teachers',
                  'coursechapter']

        # fields = '__all__'

    def get_recommend_courses(self, obj):
        """获取推荐的所有课程"""

        queryset = obj.recommend_courses.all()
        return [{'id': row.id, 'name': row.name} for row in queryset]

    def get_teachers(self, obj):
        """获取所有老师"""
        obj = obj.teachers.all()
        return [{'id': row.id, 'name': row.name} for row in obj]

    def get_coursechapter(self, obj):
        """获取所有章节"""
        obj = obj.course.coursechapters.all()

        return [{'id': row.id, } for row in obj]
