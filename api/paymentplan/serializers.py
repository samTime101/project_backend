from rest_framework import serializers
from sql.models import PaymentPlan

class PaymentPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentPlan
        fields = [
            'id', 'title', 'amount', 'description', 'due_date',
            'status', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'created_at']