import smtplib
import json
from pure_pagination import Paginator, EmptyPage, PageNotAnInteger

from django.shortcuts import render
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.views.generic.base import View
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

from .models import UserPorfile, EmailVerifyRecord, Banner
from .forms import LoginForm, RegisterForm, ForgetForm, ModifyPwdForm, UploadImageForm, UserInfoForm
from utils.email_send import send_register_email
from utils.mixin_utils import LoginRequiredMixin
from operation.models import UserCourse, UserFavorite, UserMessage
from orgenization.models import CourseOrg, Teacher
from courses.models import Course
# Create your views here.


class CustomBackend(ModelBackend):
	'''
	兼容邮箱登录和用户名登录
	'''
	def authenticate(self, request, username=None, password=None, **kwargs):
		try:
			user = UserPorfile.objects.get(Q(username=username) | Q(email=username))
			if user.check_password(password):
				return user
		except Exception as e:
			return None


class AciveUserView(View):
	'''
	邮箱激活
	'''
	def get(self, request, active_code):
		all_records = EmailVerifyRecord.objects.filter(code=active_code)
		if all_records:
			for records in all_records:
				email = records.email
				user = UserPorfile.objects.get(email=email)
				user.is_active = True
				user.save()
		else:
			return render(request, "active_fail.html")
		return render(request, "login.html")


class RegisterView(View):
	'''
	注册用户
	'''
	def get(self, request):
		register_form = RegisterForm()
		return render(request, 'register.html', {'register_form': register_form})

	def post(self, request):
		register_form = RegisterForm(request.POST)
		if register_form.is_valid():
			user_name = request.POST.get("email", "")
			if UserPorfile.objects.filter(email=user_name):
				return render(request, 'register.html', {"register_form":register_form, "msg":"用户已经存在"})
			pass_word = request.POST.get("password", "")
			users_profile = UserPorfile()
			users_profile.username = user_name
			users_profile.email = user_name
			users_profile.password = make_password(pass_word)
			users_profile.is_active = False
			users_profile.save()

			# 写入欢迎注册的消息
			user_message = UserMessage()
			user_message.user = users_profile.id
			user_message.message = "欢迎注册"
			user_message.save()

			try:
				send_register_email(user_name, "register")
			except smtplib.SMTPRecipientsRefused:
				return render(request, 'register.html', {"register_form": register_form, "msg": "邮件发送失败"})
			return render(request, "login.html")
		else:
			return render(request, 'register.html', {'register_form': register_form})


class LoginView(View):
	'''
	用户登录
	'''
	def get(self, request):
		return render(request, 'login.html', {})

	def post(self, request):
		login_form = LoginForm(request.POST)
		if login_form.is_valid():
			user_name = request.POST.get("username", "")
			pass_word = request.POST.get("password", "")
			user = authenticate(username=user_name, password=pass_word)
			if user is not None:
				if user.is_active:
					login(request, user)
					return HttpResponseRedirect(reverse("index"))
				else:
					return render(request, "login.html", {"msg": "邮箱未验证"})
			else:
				return render(request, "login.html", {"msg": "用户名或者密码错误"})
		else:
			return render(request, "login.html", {"login_form": login_form})


class LogoutView(View):
	'''
	登出
	'''
	def get(self, request):
		logout(request)
		return HttpResponseRedirect(reverse("index"))


class ForgetPwdView(View):
	'''
	找回密码
	'''
	def get(self, request):
		forget_form = ForgetForm()
		return render(request, "forgetpwd.html", {'forget_form': forget_form})

	def post(self, request):
		forget_form = ForgetForm(request.POST)
		if forget_form.is_valid():
			email = request.POST.get("email", "")
			send_register_email(email, "forget")
			return render(request, "send_success.html")
		else:
			return render(request, "forgetpwd.html", {'forget_form': forget_form})


class ResetView(View):
	'''
	处理点击链接后页面显示
	'''
	def get(self, request, reset_code):
		all_records = EmailVerifyRecord.objects.filter(code=reset_code)
		if all_records:
			for records in all_records:
				email = records.email
				return render(request, "password_reset.html", {"email": email})
		else:
			return render(request, "active_fail.html")
		return render(request, "login.html")


class ModifyPwdView(View):
	'''
	修改密码后post请求
	'''
	def post(self, request):
		modify_form = ModifyPwdForm(request.POST)
		if modify_form.is_valid():
			pwd = request.POST.get("password", "")
			pwd2 = request.POST.get("password2", "")
			email = request.POST.get("email", "")
			if pwd != pwd2:
				return render(request, "password_reset.html", {"email":email, "msg": "密码不一致"})
			else:
				user = UserPorfile.objects.get(email=email)
				user.password = make_password(pwd2)
				user.save()
				return render(request, "login.html")
		else:
			email = request.POST.get("email", "")
			return render(request, "password_reset.html", {"email": email, "modify_form": modify_form})


class UserinfoView(LoginRequiredMixin, View):
	'''
	用户个人信息
	'''
	def get(self, request):
		return render(request, 'usercenter-info.html',{})

	def post(self, request):
		user_info_form = UserInfoForm(request.POST, instance=request.user)
		if user_info_form.is_valid():
			user_info_form.save()
			return HttpResponse('{"status":"success"}', content_type='application/json')
		else:
			return HttpResponse(json.dumps(user_info_form.errors), content_type='application/json')


class UploadImageView(LoginRequiredMixin, View):
	'''
	用户修改头像
	'''
	# def post(self, request):
	# 	image_form = UploadImageForm(request.POST, request.FILES)
	# 	if image_form.is_valid():
	# 		image = image_form.cleaned_data['image']
	# 		request.user.image = image
	# 		request.user.save()

	def post(self, request):
		image_form = UploadImageForm(request.POST, request.FILES, instance=request.user)
		if image_form.is_valid():
			image_form.save()
			return HttpResponse('{"status":"success"}', content_type='application/json')
		else:
			return HttpResponse('{"fail":"success"}', content_type='application/json')


class UpdatePwdView(View):
	"""
    个人中心修改用户密码
    """

	def post(self, request):
		modify_form = ModifyPwdForm(request.POST)
		if modify_form.is_valid():

			pwd1 = request.POST.get("password", "")
			pwd2 = request.POST.get("password2", "")
			if pwd1 != pwd2:
				return HttpResponse('{"status":"fail","msg":"密码不一致"}', content_type='application/json')
			user = request.user
			user.password = make_password(pwd2)
			user.save()
			return HttpResponse('{"status":"success"}', content_type='application/json')

		else:
			return HttpResponse(json.dumps(modify_form.errors), content_type='application/json')


class SendEmailCodeView(View):
	'''
	发送邮箱验证码
	'''
	def get(self, request):
		email = request.GET.get('email', '')

		if UserPorfile.objects.filter(email=email):
			return HttpResponse('{"email":"邮箱已经存在"}', content_type='application/json')
		send_register_email(email, "update_email")
		return HttpResponse('{"status":"success"}', content_type='application/json')


class UpdateEmailView(View):
	'''
	修改邮箱
	'''

	def post(self, request):
		email = request.POST.get('email', '')
		code = request.POST.get('code', '')

		existed_records = EmailVerifyRecord.objects.filter(email=email, code=code, send_type='update_email')
		if existed_records:
			user = request.user
			user.email = email
			user.save()
			return HttpResponse('{"status":"success"}', content_type='application/json')
		else:
			return HttpResponse('{"email":"验证码出错"}', content_type='application/json')


class MyCourseView(LoginRequiredMixin, View):
	'''
	我的课程
	'''

	def get(self, request):
		user_courses = UserCourse.objects.filter(user=request.user)
		return render(request, 'usercenter-mycourse.html', {
			'user_courses': user_courses
		})


class MyFavOrgView(LoginRequiredMixin, View):
	'''
	我的收藏课程机构
	'''

	def get(self, request):
		orgs_list = []
		fav_orgs = UserFavorite.objects.filter(user=request.user, fav_type=2)
		for fav_org in fav_orgs:
			org_id = fav_org.fav_id
			org = CourseOrg.objects.get(id=org_id)
			orgs_list.append(org)
		return render(request, 'usercenter-fav-org.html', {
			'orgs_list': orgs_list
		})


class MyFavTeacherView(LoginRequiredMixin, View):
	'''
	我的收藏讲师
	'''

	def get(self, request):
		teachers_list = []
		fav_teachers = UserFavorite.objects.filter(user=request.user, fav_type=3)
		for fav_org in fav_teachers:
			teacher_id = fav_org.fav_id
			teacher = Teacher.objects.get(id=teacher_id)
			teachers_list.append(teacher)

		return render(request, 'usercenter-fav-teacher.html', {
			'teachers_list': teachers_list
		})


class MyFavCourseView(LoginRequiredMixin, View):
	'''
	我的收藏课程
	'''

	def get(self, request):
		course_list = []
		fav_courses = UserFavorite.objects.filter(user=request.user, fav_type=1)
		for fav_course in fav_courses:
			course_id = fav_course.fav_id
			course = Course.objects.get(id=course_id)
			course_list.append(course)

		return render(request, 'usercenter-fav-course.html', {
			'course_list': course_list
		})


class MymessageView(View):
	'''
	我的消息
	'''

	def get(self, request):
		all_messages = UserMessage.objects.filter(user=request.user.id)

		# 用户进入个人消息页面后清空未读消息的记录
		all_unread_messages = UserMessage.objects.filter(user=request.user.id, has_read=False)
		for unread_message in all_unread_messages:
			unread_message.has_read = True
			unread_message.save()

		# 对个人消息进行分页
		try:
			page = request.GET.get('page', 1)
		except PageNotAnInteger:
			page = 1

		p = Paginator(all_messages, 5, request=request)

		messages = p.page(page)
		return render(request, 'usercenter-message.html', {
			"messages": messages
		})


class IndexView(View):
	'''
	首页
	'''
	def get(self, request):

		# 取出轮播图
		all_banners = Banner.objects.all().order_by('index')

		# 取出课程
		courses = Course.objects.filter(is_banner=False)[:6]
		banner_courses = Course.objects.filter(is_banner=True)[:3]

		# 取出机构
		course_orgs = CourseOrg.objects.all()[:15]

		return render(request, 'index.html',{
			'all_banners': all_banners,
			'courses': courses,
			'banner_courses': banner_courses,
			'course_orgs': course_orgs
		})


# 全局404处理函数
def page_not_found(request):
	from django.shortcuts import render_to_response
	response = render_to_response('404.html', {})
	response.status_code = 404
	return response


# 全局500处理函数
def page_error(request):
	from django.shortcuts import render_to_response
	response = render_to_response('500.html', {})
	response.status_code = 500
	return response