from rest_framework import serializers


PACK_CATALOG = {
    'data': [
        {'amount': 35, 'slug': '1day-data-pack', 'title': 'Rs 35 Data Pack'},
        {'amount': 40, 'slug': 'rs-40-1day', 'title': 'Rs 40 1 Day Data'},
        {'amount': 50, 'slug': '50-ul-combo', 'title': 'Rs 50 UL Combo'},
        {'amount': 99, 'slug': '99-ul-combo', 'title': 'Rs 99 UL Combo'},
    ],
    'voice': [
        {'amount': 18, 'slug': '1-day-voice-18', 'title': 'Rs 18 Voice Pack'},
        {'amount': 22, 'slug': 'day-1-day-unlimited-voice-pack', 'title': 'Rs 22 Unlimited Voice'},
        {'amount': 25, 'slug': '1-day-all-nepal-voice-1', 'title': 'Rs 25 All Nepal Voice'},
        {'amount': 30, 'slug': '1-day-unlimited-ncell-voice-1', 'title': 'Rs 30 Unlimited Ncell Voice'},
        {'amount': 39, 'slug': 'rs-50-day-unlimited-voice', 'title': 'Rs 39 Unlimited Voice'},
        {'amount': 50, 'slug': 'rs-50-day-unlimited-voice', 'title': 'Rs 50 Unlimited Voice'},
        {'amount': 99, 'slug': 'rs-99-ul-all-nepal', 'title': 'Rs 99 UL All Nepal'},
        {'amount': 199, 'slug': 'rs-199-all-nepal', 'title': 'Rs 199 All Nepal'},
        {'amount': 299, 'slug': 'rs-299-unlimited-all-nepal', 'title': 'Rs 299 Unlimited All Nepal'},
        {'amount': 599, 'slug': 'rs-599-all-nepal', 'title': 'Rs 599 All Nepal'},
    ],
}


def get_pack_details(pack_type, amount):
    for pack in PACK_CATALOG.get(pack_type, []):
        if pack['amount'] == amount:
            return pack
    return None


class NcellPackSelectionSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=10)
    pack_type = serializers.ChoiceField(choices=[('data', 'Data'), ('voice', 'Voice')])
    amount = serializers.IntegerField(min_value=1)

    def validate_phone_number(self, value):
        phone_number = ''.join(ch for ch in value if ch.isdigit())
        if len(phone_number) != 10:
            raise serializers.ValidationError('Enter a valid 10-digit mobile number.')
        return phone_number

    def validate(self, attrs):
        pack = get_pack_details(attrs['pack_type'], attrs['amount'])
        if not pack:
            raise serializers.ValidationError({'amount': 'Selected pack is not available.'})
        attrs['pack'] = pack
        return attrs


class NcellSendOtpSerializer(NcellPackSelectionSerializer):
    pass


class NcellConfirmPurchaseSerializer(NcellPackSelectionSerializer):
    token = serializers.CharField()
    otp_code = serializers.CharField(max_length=6)

    def validate_otp_code(self, value):
        otp_code = ''.join(ch for ch in value if ch.isdigit())
        if len(otp_code) != 6:
            raise serializers.ValidationError('Enter the 6-digit OTP code.')
        return otp_code

