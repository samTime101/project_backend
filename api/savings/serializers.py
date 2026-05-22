from rest_framework import serializers
from sql.models import SavingsGoal

class SavingsGoalSerializer(serializers.ModelSerializer):
    progress_percentage = serializers.ReadOnlyField()
    image = serializers.SerializerMethodField(read_only=True)
    image_file = serializers.FileField(write_only=True, required=False, allow_null=True)
    remove_image = serializers.BooleanField(write_only=True, required=False, default=False)

    class Meta:
        model = SavingsGoal
        fields = ['id', 'title', 'image', 'image_file', 'remove_image', 'target_amount', 'current_amount', 'due_date', 'progress_percentage', 'created_at']
        read_only_fields = ['id', 'created_at']

    def get_image(self, obj):
        request = self.context.get('request')
        if not obj.image:
            return ''
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url

    def validate_image_file(self, value):
        if not value:
            return value
        content_type = getattr(value, 'content_type', '')
        if content_type and not content_type.startswith('image/'):
            raise serializers.ValidationError('Please upload a valid image file.')
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError('Image size must be 5 MB or smaller.')
        return value

    def create(self, validated_data):
        image_file = validated_data.pop('image_file', None)
        validated_data.pop('remove_image', False)
        validated_data['image_url'] = ''
        goal = SavingsGoal(**validated_data)
        if image_file:
            goal.image = image_file
        goal.save()
        return goal

    def update(self, instance, validated_data):
        image_file = validated_data.pop('image_file', None)
        remove_image = validated_data.pop('remove_image', False)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.image_url = ''
        if remove_image and instance.image:
            instance.image.delete(save=False)
            instance.image = None
        if image_file:
            if instance.image:
                instance.image.delete(save=False)
            instance.image = image_file
        instance.save()
        return instance
