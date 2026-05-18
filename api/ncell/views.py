import requests
import urllib3
import re
from django.conf import settings
from django.db import transaction as db_transaction
from requests import RequestException
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from sql.models import Expense, Transaction
from .serializers import PACK_CATALOG, NcellConfirmPurchaseSerializer, NcellSendOtpSerializer


NCELL_SEND_OTP_URL = 'https://webapi.ncell.com.np/v1/send-otp'
NCELL_BUY_REQUEST_URL = 'https://webapi.ncell.com.np/v1/pack/buy/request/balance'
NCELL_SUCCESS_CODE = 400200

if not settings.NCELL_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _extract_ncell_message(payload):
    return payload.get('errors') or payload.get('message') or 'Ncell request failed.'


def _post_to_ncell(url, payload):
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://www.ncell.com.np',
        'Referer': f'{settings.NCELL_REDIRECT_URL}/',
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/136.0.0.0 Safari/537.36'
        ),
    }
    response = requests.post(
        url,
        json=payload,
        headers=headers,
        timeout=settings.NCELL_TIMEOUT_SECONDS,
        verify=settings.NCELL_VERIFY_SSL,
    )
    try:
        return response.json()
    except ValueError as exc:
        response.raise_for_status()
        raise RequestException('Invalid response from Ncell') from exc


def _get_ncell_order_page(url):
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Referer': settings.NCELL_REDIRECT_URL,
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/136.0.0.0 Safari/537.36'
        ),
    }
    response = requests.get(
        url,
        headers=headers,
        timeout=settings.NCELL_TIMEOUT_SECONDS,
        verify=settings.NCELL_VERIFY_SSL,
    )
    response.raise_for_status()
    return response.text


def _extract_html_text(pattern, html):
    match = re.search(pattern, html, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return re.sub(r'\s+', ' ', match.group(1)).strip()


def _parse_order_result(html):
    transaction_id = _extract_html_text(
        r'Transaction ID:\s*<span>\s*([^<]+)\s*</span>',
        html,
    )

    if re.search(r'Insufficient Balance', html, flags=re.IGNORECASE):
        current_balance = _extract_html_text(
            r'Currently you have.*?Rs\.\s*<!-- -->\s*([^<\s]+)',
            html,
        )
        recharge_amount = _extract_html_text(
            r'Please recharge.*?Rs\.\s*<!-- -->\s*([^<\s]+)',
            html,
        )
        return {
            'status': 'insufficient_balance',
            'transaction_id': transaction_id,
            'current_balance': current_balance,
            'required_recharge': recharge_amount,
        }

    if re.search(r'Thank you for your purchase\. A confirmation SMS will be sent to your number\.', html, flags=re.IGNORECASE):
        return {
            'status': 'success',
            'transaction_id': transaction_id,
        }

    return {
        'status': 'unknown',
        'transaction_id': transaction_id,
    }


def _ncell_gateway_error(exc):
    message = 'Could not reach Ncell right now. Please try again shortly.'
    if settings.DEBUG:
        message = f'Ncell upstream request failed: {exc}'
    return Response({'detail': message}, status=status.HTTP_502_BAD_GATEWAY)


class NcellPackCatalogView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'data': PACK_CATALOG,
        })


class NcellSendOtpView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = NcellSendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if request.user.balance < serializer.validated_data['amount']:
            return Response(
                {'detail': f'Insufficient balance. You need NPR {serializer.validated_data["amount"]:.2f} to buy this pack.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = {
            'phoneNumber': serializer.validated_data['phone_number'],
            'redirectUrl': settings.NCELL_REDIRECT_URL,
            'slug': serializer.validated_data['pack']['slug'],
        }

        try:
            ncell_response = _post_to_ncell(NCELL_SEND_OTP_URL, payload)
        except RequestException as exc:
            return _ncell_gateway_error(exc)

        if ncell_response.get('statusCode') != NCELL_SUCCESS_CODE:
            return Response(
                {
                    'detail': _extract_ncell_message(ncell_response),
                    'statusCode': ncell_response.get('statusCode'),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response({
            'message': 'OTP sent successfully.',
            'statusCode': ncell_response.get('statusCode'),
            'token': ncell_response.get('data', {}).get('token'),
            'pack': serializer.validated_data['pack'],
            'phoneNumber': serializer.validated_data['phone_number'],
        })


class NcellConfirmPurchaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = NcellConfirmPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if request.user.balance < serializer.validated_data['amount']:
            return Response(
                {'detail': f'Insufficient balance. You need NPR {serializer.validated_data["amount"]:.2f} to buy this pack.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = {
            'phoneNumber': serializer.validated_data['phone_number'],
            'redirectUrl': settings.NCELL_REDIRECT_URL,
            'slug': serializer.validated_data['pack']['slug'],
            'token': serializer.validated_data['token'],
            'otpCode': serializer.validated_data['otp_code'],
        }

        try:
            ncell_response = _post_to_ncell(NCELL_BUY_REQUEST_URL, payload)
        except RequestException as exc:
            return _ncell_gateway_error(exc)

        if ncell_response.get('statusCode') != NCELL_SUCCESS_CODE:
            return Response(
                {
                    'detail': _extract_ncell_message(ncell_response),
                    'statusCode': ncell_response.get('statusCode'),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        redirect_url = ncell_response.get('data', {}).get('redirectUrl')

        try:
            order_html = _get_ncell_order_page(redirect_url)
        except RequestException as exc:
            return _ncell_gateway_error(exc)

        order_result = _parse_order_result(order_html)

        if order_result['status'] == 'insufficient_balance':
            current_balance = order_result.get('current_balance')
            recharge_amount = order_result.get('required_recharge')
            detail = 'Ncell reported insufficient balance for this purchase.'
            if current_balance and recharge_amount:
                detail = (
                    f'Ncell balance insufficient. Current Ncell balance: Rs. {current_balance}. '
                    f'Please recharge Rs. {recharge_amount} to buy this offer.'
                )
            return Response(
                {
                    'detail': detail,
                    'statusCode': ncell_response.get('statusCode'),
                    'transactionId': order_result.get('transaction_id'),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if order_result['status'] != 'success':
            return Response(
                {
                    'detail': 'Could not verify the Ncell purchase result.',
                    'statusCode': ncell_response.get('statusCode'),
                    'transactionId': order_result.get('transaction_id'),
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        with db_transaction.atomic():
            transaction_record = Transaction.objects.create(
                initiator=request.user,
                target=request.user,
                transaction_type='SEND',
                status='COMPLETED',
                amount=serializer.validated_data['amount'],
                description=serializer.validated_data['pack']['title'],
                service_label='Ncell Datapack',
            )

            Expense.objects.create(
                user=request.user,
                type='Expense',
                amount=serializer.validated_data['amount'],
                category='Ncell Datapack',
                description=serializer.validated_data['pack']['title'],
            )

        return Response({
            'message': 'Ncell pack purchased successfully.',
            'statusCode': ncell_response.get('statusCode'),
            'pack': serializer.validated_data['pack'],
            'phoneNumber': serializer.validated_data['phone_number'],
            'transactionId': transaction_record.id,
            'providerTransactionId': order_result.get('transaction_id'),
        })
