import json
import urllib3

import requests
from django.conf import settings
from django.db import transaction as db_transaction
from requests import HTTPError, RequestException
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from sql.models import Expense, Transaction
from utils.bypass import ReCaptchaV3Bypass
from .serializers import PACK_CATALOG, NtcConfirmPurchaseSerializer, NtcSendOtpSerializer


NTC_SUBSCRIBE_URL = 'https://cms.ntc.net.np/api/subscribeVas'

if not settings.NTC_VERIFY_SSL:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _mask_debug_payload(payload):
    masked = dict(payload)
    if masked.get('recaptchaToken'):
        token = str(masked['recaptchaToken'])
        masked['recaptchaToken'] = f'{token[:24]}...({len(token)} chars)'
    return masked


def _safe_json_from_response(response):
    try:
        return response.json()
    except ValueError:
        return None


def _extract_response_text(response):
    text = (response.text or '').strip()
    return text[:4000]


def _build_ntc_debug_data(payload, response=None, error=None):
    debug_data = {
        'endpoint': NTC_SUBSCRIBE_URL,
        'requestPayload': _mask_debug_payload(payload),
    }

    if response is not None:
        debug_data.update({
            'statusCode': response.status_code,
            'responseHeaders': dict(response.headers),
            'responseBody': _safe_json_from_response(response) or _extract_response_text(response),
        })

    if error is not None:
        debug_data['error'] = str(error)

    return debug_data


def _log_ntc_debug(label, payload, response=None, error=None):
    if not settings.DEBUG:
        return
    debug_data = _build_ntc_debug_data(payload, response=response, error=error)
    print(f'[NTC DEBUG] {label}')
    print(json.dumps(debug_data, indent=2, ensure_ascii=True, default=str))


def _ntc_gateway_error(exc, payload=None, response=None):
    message = 'Could not reach Nepal Telecom right now. Please try again shortly.'
    body = {'detail': message}
    if settings.DEBUG and payload is not None:
        body['debug'] = _build_ntc_debug_data(payload, response=response, error=exc)
        _log_ntc_debug('gateway_error', payload, response=response, error=exc)
    return Response(body, status=status.HTTP_502_BAD_GATEWAY)


def _extract_ntc_message(payload, default='Nepal Telecom request failed.'):
    if isinstance(payload, dict):
        return payload.get('message') or payload.get('detail') or default
    return default


def _get_recaptcha_token():
    if not settings.NTC_URL:
        raise RequestException('NTC_URL is not configured.')

    gtk = ReCaptchaV3Bypass(settings.NTC_URL).bypass()
    if not gtk:
        raise RequestException('Could not generate Nepal Telecom reCAPTCHA token.')
    return gtk


def _post_to_ntc(payload):
    payload['recaptchaToken'] = _get_recaptcha_token()
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Content-Type': 'application/json',
        'Origin': 'https://ntc.net.np',
        'Referer': 'https://ntc.net.np/',
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/136.0.0.0 Safari/537.36'
        ),
    }
    _log_ntc_debug('outgoing_request', payload)

    response = requests.post(
        NTC_SUBSCRIBE_URL,
        json=payload,
        headers=headers,
        timeout=settings.NTC_TIMEOUT_SECONDS,
        verify=settings.NTC_VERIFY_SSL,
    )
    _log_ntc_debug('incoming_response', payload, response=response)
    return response


def _parse_ntc_response(payload, response):
    try:
        data = response.json()
    except ValueError as exc:
        raise RequestException(
            f'Invalid response from Nepal Telecom: {_extract_response_text(response)}'
        ) from exc

    try:
        response.raise_for_status()
    except HTTPError as exc:
        error = RequestException(
            f'{exc}. Upstream body: {json.dumps(data, ensure_ascii=True)[:4000]}'
        )
        setattr(error, 'ntc_response', response)
        raise error from exc

    return data


def _ntc_error_response(detail, status_code, payload, response=None, extra=None):
    body = {'detail': detail}
    if extra:
        body.update(extra)
    if settings.DEBUG:
        body['debug'] = _build_ntc_debug_data(payload, response=response)
    return Response(body, status=status_code)


def _get_ntc_message_from_exception(exc):
    response = getattr(exc, 'ntc_response', None)
    if response is None:
        return None
    data = _safe_json_from_response(response)
    return _extract_ntc_message(data, default=None)


class NtcPackCatalogView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({
            'data': PACK_CATALOG,
        })


class NtcSendOtpView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = NtcSendOtpSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if request.user.balance < serializer.validated_data['pack']['amount']:
            return Response(
                {'detail': f'Insufficient balance. You need NPR {serializer.validated_data["pack"]["amount"]:.2f} to buy this pack.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = {
            'package_id': serializer.validated_data['pack']['p_id'],
            'phone': serializer.validated_data['phone_number'],
            'BusiCode': serializer.validated_data['pack']['busicode'],
        }

        try:
            ntc_http_response = _post_to_ntc(payload)
            ntc_response = _parse_ntc_response(payload, ntc_http_response)
        except RequestException as exc:
            ntc_message = _get_ntc_message_from_exception(exc)
            if ntc_message == 'Please request after 2 minutes of previous order':
                return _ntc_error_response(
                    'Please wait 2 minutes before requesting another OTP for this number.',
                    status.HTTP_400_BAD_REQUEST,
                    payload,
                    response=getattr(exc, 'ntc_response', None),
                )
            return _ntc_gateway_error(exc, payload=payload, response=getattr(exc, 'ntc_response', None))

        if ntc_response.get('message') == 'Subscription successfully added.':
            return _ntc_error_response(
                'Nepal Telecom activated the pack without OTP verification.',
                status.HTTP_502_BAD_GATEWAY,
                payload,
                response=ntc_http_response,
            )

        if ntc_response.get('message') == 'No sufficient balance':
            return _ntc_error_response(
                'Nepal Telecom reported insufficient balance for this purchase.',
                status.HTTP_400_BAD_REQUEST,
                payload,
                response=ntc_http_response,
            )

        body = {
            'message': _extract_ntc_message(ntc_response, 'OTP request submitted successfully.'),
            'otpRequired': bool(ntc_response.get('otp', True)),
            'pack': serializer.validated_data['pack'],
            'phoneNumber': serializer.validated_data['phone_number'],
        }
        if settings.DEBUG:
            body['debug'] = _build_ntc_debug_data(payload, response=ntc_http_response)
        return Response(body)


class NtcConfirmPurchaseView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = NtcConfirmPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if request.user.balance < serializer.validated_data['pack']['amount']:
            return Response(
                {'detail': f'Insufficient balance. You need NPR {serializer.validated_data["pack"]["amount"]:.2f} to buy this pack.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        payload = {
            'package_id': serializer.validated_data['pack']['p_id'],
            'phone': serializer.validated_data['phone_number'],
            'BusiCode': serializer.validated_data['pack']['busicode'],
            'otp': serializer.validated_data['otp_code'],
        }

        try:
            ntc_http_response = _post_to_ntc(payload)
            ntc_response = _parse_ntc_response(payload, ntc_http_response)
        except RequestException as exc:
            ntc_message = _get_ntc_message_from_exception(exc)
            if ntc_message == 'No sufficient balance':
                return _ntc_error_response(
                    'No sufficient balance',
                    status.HTTP_400_BAD_REQUEST,
                    payload,
                    response=getattr(exc, 'ntc_response', None),
                )
            if ntc_message == 'Please request after 2 minutes of previous order':
                return _ntc_error_response(
                    'Please wait 2 minutes before trying this Nepal Telecom purchase again.',
                    status.HTTP_400_BAD_REQUEST,
                    payload,
                    response=getattr(exc, 'ntc_response', None),
                )
            return _ntc_gateway_error(exc, payload=payload, response=getattr(exc, 'ntc_response', None))

        message = ntc_response.get('message')
        if message == 'Otp verification failed.':
            return _ntc_error_response(
                message,
                status.HTTP_400_BAD_REQUEST,
                payload,
                response=ntc_http_response,
                extra={'otp': False},
            )

        if message == 'No sufficient balance':
            return _ntc_error_response(
                'No sufficient balance',
                status.HTTP_400_BAD_REQUEST,
                payload,
                response=ntc_http_response,
            )

        if message != 'Subscription successfully added.':
            return _ntc_error_response(
                _extract_ntc_message(ntc_response),
                status.HTTP_502_BAD_GATEWAY,
                payload,
                response=ntc_http_response,
            )

        with db_transaction.atomic():
            transaction_record = Transaction.objects.create(
                initiator=request.user,
                target=request.user,
                transaction_type='SEND',
                status='COMPLETED',
                amount=serializer.validated_data['pack']['amount'],
                description=serializer.validated_data['pack']['title'],
                service_label='Nepal Telecom',
            )

            Expense.objects.create(
                user=request.user,
                type='Expense',
                amount=serializer.validated_data['pack']['amount'],
                category='Nepal Telecom',
                description=serializer.validated_data['pack']['title'],
            )

        body = {
            'message': 'Nepal Telecom pack purchased successfully.',
            'pack': serializer.validated_data['pack'],
            'phoneNumber': serializer.validated_data['phone_number'],
            'transactionId': transaction_record.id,
            'providerMessage': message,
        }
        if settings.DEBUG:
            body['debug'] = _build_ntc_debug_data(payload, response=ntc_http_response)
        return Response(body)
