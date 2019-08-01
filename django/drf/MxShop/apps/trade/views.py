from datetime import datetime

from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework import mixins
from django.shortcuts import redirect

from utils.permissions import IsOwnerOrReadOnly
from .serializers import ShopCartSerializer, ShopCartDetailSerializer, OrderSerializer, OrderDetailSerializer
from .models import ShoppingCart, OrderInfo, OrderGoods


class ShoppingCartViewset(viewsets.ModelViewSet):
	"""
	购物车功能
	list:
		获取购物车详情
	create：
		加入购物车
	delete：
		删除购物记录
	"""

	permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
	authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
	serializer_class = ShopCartSerializer
	lookup_field = "goods_id"

	def perform_create(self, serializer):
		shop_cart = serializer.save()
		goods = shop_cart.goods
		goods.goods_num -= shop_cart.nums
		goods.save()

	def perform_destroy(self, instance):
		goods = instance.goods
		goods.goods_num += instance.nums
		goods.save()
		instance.delete()

	def perform_update(self, serializer):
		# 取到保存之前的数据和现在的数据进行比对
		existed_record = ShoppingCart.objects.get(id=serializer.id)
		existed_nums = existed_record.nums
		saved_record = serializer.save()
		nums = saved_record-existed_nums
		goods = saved_record.goods
		goods.goods_num -= nums
		goods.save()

	def get_serializer_class(self):
		if self.action == 'list':
			return ShopCartDetailSerializer
		else:
			return ShopCartSerializer

	def get_queryset(self):
		return ShoppingCart.objects.filter(user=self.request.user)


class OrderViewset(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.DestroyModelMixin, viewsets.GenericViewSet):
	"""
	订单管理
	list:
		获取个人订单
	delete:
		删除订单
	create：
		新增订单
	"""
	permission_classes = (IsAuthenticated, IsOwnerOrReadOnly)
	authentication_classes = (JSONWebTokenAuthentication, SessionAuthentication)
	serializer_class = OrderSerializer

	def get_serializer_class(self):
		if self.action == "retrieve":
			return OrderDetailSerializer
		return OrderSerializer

	def get_queryset(self):
		return OrderInfo.objects.filter(user=self.request.user)

	def perform_create(self, serializer):
		order = serializer.save()
		shop_carts = ShoppingCart.objects.filter(user=self.request.user)
		for shop_cart in shop_carts:
			order_goods = OrderGoods()
			order_goods.goods = shop_cart.goods
			order_goods.goods_num = shop_cart.nums
			order_goods.order = order
			order_goods.save()

			shop_cart.delete()
		return order


from rest_framework.views import APIView
from utils.alipay import AliPay
from MxShop.settings import ali_pub_key_path, private_key_path
from rest_framework.response import Response


class AlipayView(APIView):

	def get(self, request):
		"""
		处理支付宝的 return_url 返回
		"""
		processed_dict = {}
		for key, value in request.GET.items():
			processed_dict[key] = value

		sign = processed_dict.pop("sign", None)

		alipay = AliPay(
			appid="",
			app_notify_url="http://192.168.153.153:8000/alipay/return/",
			app_private_key_path=private_key_path,
			alipay_public_key_path=ali_pub_key_path,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
			debug=True,  # 默认False,
			return_url="http://192.168.153.153:8000/alipay/return/"
		)

		verify_re = alipay.verify(processed_dict, sign)

		if verify_re is True:
			order_sn = processed_dict.get('out_trade_no', None)
			trade_no = processed_dict.get('trade_no', None)
			trade_status = processed_dict.get('trade_status', None)

			existed_orders = OrderInfo.objects.filter(order_sn=order_sn)
			for existed_order in existed_orders:
				existed_order.pay_status = trade_status
				existed_order.trade_no = trade_no
				existed_order.pay_time = datetime.now()
				existed_order.save()

			# 跳转到index页面
			response = redirect("index")
			# 设置 cookie ,vue取到 cookie 跳转到 pay 页面
			response.set_cookie("nextPath", "pay", max_age=3)
			return response
		else:
			# 验证失败直接到首页
			response = redirect("index")
			return response


	def post(self, request):

		"""
		处理支付宝的 notify_url
		"""

		processed_dict = {}
		for key, value in request.POST.items():
			processed_dict[key] = value

		sign = processed_dict.pop("sign", None)

		alipay = AliPay(
			appid="2016091100485730",
			app_notify_url="http://192.168.153.153:8000/alipay/return/",
			app_private_key_path=private_key_path,
			alipay_public_key_path=ali_pub_key_path,  # 支付宝的公钥，验证支付宝回传消息使用，不是你自己的公钥,
			debug=True,  # 默认False,
			return_url="http://192.168.153.153:8000/alipay/return/"
		)

		# 支付宝返回的数据验证
		verify_re = alipay.verify(processed_dict, sign)

		if verify_re is True:
			order_sn = processed_dict.get('out_trade_no', None)
			trade_no = processed_dict.get('trade_no', None)
			trade_status = processed_dict.get('trade_status', None)

			existed_orders = OrderInfo.objects.filter(order_sn=order_sn)

			for existed_order in existed_orders:

				# 销量修改
				order_goods = existed_order.goods.all()
				for order_good in order_goods:
					goods = order_good.goods
					goods.sold_num += order_good.goods_num
					goods.save()

				existed_order.pay_status = trade_status
				existed_order.trade_no = trade_no
				existed_order.pay_time = datetime.now()
				existed_order.save()

			return Response("success")

