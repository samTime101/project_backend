from rest_framework import serializers
from sql.models import SavingsGoal

class SavingsGoalSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.ReadOnlyField()

    class Meta:
        model = SavingsGoal
        fields = ['id', 'title', 'target_amount', 'current_amount', 'due_date', 'progress_percentage', 'created_at']
        read_only_fields = ['id', 'created_at']
