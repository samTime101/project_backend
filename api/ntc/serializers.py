from rest_framework import serializers


PACK_CATALOG = {
    'data': [
        {
            'p_id': 540,
            'title': '600 MB Data Pack for 1 day',
            'amount': 22,
            'validity': '1 Day',
            'busicode': '20241008101',
        },
        {
            'p_id': 77,
            'title': '1 GB Data Pack for 1 day',
            'amount': 30,
            'validity': '1 Day',
            'busicode': '8201805080702',
        },
        {
            'p_id': 83,
            'title': '4 GB Data Pack for 1 day',
            'amount': 99,
            'validity': '1 Day',
            'busicode': '201705120201',
        },
        {
            'p_id': 200,
            'title': 'Unlimited Pack(NT-NT Voice/Data) for within 1 hour from now',
            'amount': 25,
            'validity': '60 mins from subscription',
            'busicode': '2017122113',
        },
        {
            'p_id': 370,
            'title': 'Unlimited Data for 2 Hours',
            'amount': 35,
            'validity': '2 Hours',
            'busicode': '2021041311',
        },
    ],
    'voice': [
        {
            'p_id': 5,
            'title': '30 min NT-NT All Time  Voice Pack for 1 Day',
            'amount': 18,
            'validity': '1 Day',
            'busicode': '2600000',
        },
        {
            'p_id': 313,
            'title': 'Unlimited NT-NT Day Voice Pack - 5:00 AM - 5:00 PM',
            'amount': 20,
            'validity': '1 Day',
            'busicode': '20200204202',
        },
        {
            'p_id': 463,
            'title': '40 min All Net National Voice Pack for 1 Day',
            'amount': 25,
            'validity': '1 Day',
            'busicode': '20220715031',
        },
        {
            'p_id': 566,
            'title': 'Unlimited NT-NT 1 Day Voice Pack',
            'amount': 30,
            'validity': '1 Day',
            'busicode': '20250110011',
        },
        {
            'p_id': 244,
            'title': 'China Voice Call - 10 Minutes',
            'amount': 35,
            'validity': '1 Day',
            'busicode': '2019020421',
        },
        {
            'p_id': 474,
            'title': '150 min NT-NT All Time Voice Pack for 1 Day',
            'amount': 59,
            'validity': '1 Day',
            'busicode': '20230411001',
        },
        {
            'p_id': 504,
            'title': '150 min All Net National Voice Pack for 1 Day',
            'amount': 69,
            'validity': '1 Day',
            'busicode': '20240410008',
        },
        {
            'p_id': 53,
            'title': 'India Voice Call - 20 Minutes',
            'amount': 80,
            'validity': '1 day',
            'busicode': '2018020788',
        },
        {
            'p_id': 248,
            'title': 'China Voice Call - 45 Minutes',
            'amount': 150,
            'validity': '7 Days',
            'busicode': '2019020431',
        },
        {
            'p_id': 627,
            'title': 'Voice Pack_333min_30days',
            'amount': 189,
            'validity': '30 days',
            'busicode': '20260423011',
        },
    ],
}


def get_pack_details(pack_type, package_id):
    for pack in PACK_CATALOG.get(pack_type, []):
        if pack['p_id'] == package_id:
            return pack
    return None


class NtcPackSelectionSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=10)
    pack_type = serializers.ChoiceField(choices=[('data', 'Data'), ('voice', 'Voice')])
    package_id = serializers.IntegerField(min_value=1)

    def validate_phone_number(self, value):
        phone_number = ''.join(ch for ch in value if ch.isdigit())
        if len(phone_number) != 10:
            raise serializers.ValidationError('Enter a valid 10-digit mobile number.')
        return phone_number

    def validate(self, attrs):
        pack = get_pack_details(attrs['pack_type'], attrs['package_id'])
        if not pack:
            raise serializers.ValidationError({'package_id': 'Selected pack is not available.'})
        attrs['pack'] = pack
        return attrs


class NtcSendOtpSerializer(NtcPackSelectionSerializer):
    pass


class NtcConfirmPurchaseSerializer(NtcPackSelectionSerializer):
    otp_code = serializers.CharField(max_length=6)

    def validate_otp_code(self, value):
        otp_code = ''.join(ch for ch in value if ch.isdigit())
        if len(otp_code) != 6:
            raise serializers.ValidationError('Enter the 6-digit OTP code.')
        return otp_code
