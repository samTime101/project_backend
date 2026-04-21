from rest_framework import serializers
from sql.models import PaymentPlan

class PaymentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentPlan
        fields = ['id', 'user', 'title', 'amount', 'description', 'due_date', 'status', 'created_at']
        read_only_fields = ['id', 'created_at', 'status', 'user']