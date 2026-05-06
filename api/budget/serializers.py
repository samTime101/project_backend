from rest_framework import serializers
from sql.models import Budget

class BudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Budget
        fields = ['id', 'category', 'amount_limit', 'period', 'created_at']
        read_only_fields = ['id', 'created_at']
