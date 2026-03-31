from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import action
from rest_framework.response import Response
from sql.models import PaymentPlan
from .serializers import PaymentPlanSerializer

class PaymentPlanViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = PaymentPlanSerializer

    def get_queryset(self):
        return PaymentPlan.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        plan = self.get_object()
        if plan.status != 'PENDING':
            return Response({"error": "Plan is already completed or canceled."},status=status.HTTP_400_BAD_REQUEST)
        plan.status = 'COMPLETED'
        plan.save()
        return Response(self.get_serializer(plan).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def mark_canceled(self, request, pk=None):
        plan = self.get_object()
        if plan.status != 'PENDING':
            return Response({"error": "Plan is already completed or canceled."},status=status.HTTP_400_BAD_REQUEST)
        plan.status = 'CANCELED'
        plan.save()
        return Response(self.get_serializer(plan).data, status=status.HTTP_200_OK)