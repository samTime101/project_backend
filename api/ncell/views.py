import requests
import urllib3
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
            'message': 'OTP verified successfully.',
            'statusCode': ncell_response.get('statusCode'),
            'redirectUrl': ncell_response.get('data', {}).get('redirectUrl'),
            'pack': serializer.validated_data['pack'],
            'phoneNumber': serializer.validated_data['phone_number'],
            'transactionId': transaction_record.id,
        })
