from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from sql.models import Transaction, Expense, PaymentPlan

User = get_user_model()


class TransactionResponseSerializer(serializers.ModelSerializer):
    initiator_name = serializers.CharField(source='initiator.first_name', read_only=True)
    target_name = serializers.CharField(source='target.first_name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id', 'initiator_name', 'target_name',
            'transaction_type', 'status', 'amount', 'description', 'created_at'
        ]
        read_only_fields = fields


class TransactionCreateRequestSerializer(serializers.ModelSerializer):
    target_email = serializers.EmailField(write_only=True)
    payment_plan_id = serializers.IntegerField(required=False, write_only=True)

    class Meta:
        model = Transaction
        fields = ['target_email', 'amount', 'transaction_type', 'description', 'payment_plan_id']

    def validate_target_email(self, value):
        try:
            return User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with this email does not exist.")

    def validate_payment_plan_id(self, value):
        request = self.context.get('request')

        try:
            plan = PaymentPlan.objects.get(id=value, user=request.user)

            if plan.status != 'PENDING':
                raise serializers.ValidationError("Plan already completed or canceled.")

            if hasattr(plan, 'transaction'):
                raise serializers.ValidationError("Plan already linked to a transaction.")

            return plan

        except PaymentPlan.DoesNotExist:
            raise serializers.ValidationError("Invalid payment plan.")

    def validate(self, data):
        request = self.context.get('request')
        target_user = data['target_email']

        if request.user == target_user:
            raise serializers.ValidationError("You cannot transact with yourself.")

        if data['transaction_type'] == 'SEND' and request.user.balance < data['amount']:
            raise serializers.ValidationError("Insufficient balance.")

        return data

    def create(self, validated_data):
        initiator = self.context['request'].user
        target = validated_data.pop('target_email')
        plan = validated_data.pop('payment_plan_id', None)

        tx_type = validated_data['transaction_type']
        amount = validated_data['amount']

        with db_transaction.atomic():
            if tx_type == 'SEND':
                trans = Transaction.objects.create(
                    initiator=initiator,
                    target=target,
                    status='COMPLETED',
                    payment_plan=plan,
                    **validated_data,
                )

                Expense.objects.create(
                    user=initiator,
                    type='Expense',
                    amount=amount,
                    category='Transfer Sent'
                )

                Expense.objects.create(
                    user=target,
                    type='Income',
                    amount=amount,
                    category='Transfer Received'
                )

                if plan:
                    plan.complete_with_transaction(trans)

            else:
                trans = Transaction.objects.create(
                    initiator=initiator,
                    target=target,
                    status='PENDING',
                    payment_plan=plan,
                    **validated_data,
                )

        return trans


class TransactionCreateResponseSerializer(TransactionResponseSerializer):
    class Meta(TransactionResponseSerializer.Meta):
        pass


class TransactionRespondRequestSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['accept', 'decline'])


class TransactionRespondResponseSerializer(TransactionResponseSerializer):
    class Meta(TransactionResponseSerializer.Meta):
        pass


class TransactionCancelRequestSerializer(serializers.Serializer):
    pass


class TransactionCancelResponseSerializer(TransactionResponseSerializer):
    class Meta(TransactionResponseSerializer.Meta):
        pass