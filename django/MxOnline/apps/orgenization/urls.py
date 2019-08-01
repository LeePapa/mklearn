from django.conf.urls import url, include

from .views import OrgView, AddUserAskView, OrgHomeView, OrgCourseView, \
	OrgDescView, OrgTeacherView, AddFacView, TeacherListView, TeacherDetailView


urlpatterns = [
	# 课程机构首页
	url(r'^list/$', OrgView.as_view(), name="org_list"),
	url(r'^add_ask/$', AddUserAskView.as_view(), name="add_ask"),
	url(r'^home/(?P<org_id>\d+)/$', OrgHomeView.as_view(), name="org_home"),
	url(r'^course/(?P<org_id>\d+)/$', OrgCourseView.as_view(), name="org_course"),
	url(r'^desc/(?P<org_id>\d+)/$', OrgDescView.as_view(), name="org_desc"),
	url(r'^org_teacher/(?P<org_id>\d+)/$', OrgTeacherView.as_view(), name="org_teacher"),

	# 課程收藏
	url(r'^add_fav/$', AddFacView.as_view(), name="add_fav"),

	# 讲师列表
	url(r'^teacher/list/$', TeacherListView.as_view(), name="teacher_list"),

	# 讲师详情
	url(r'^teacher/detail/(?P<teacher_id>\d+)/$', TeacherDetailView.as_view(), name="teacher_detail"),
]