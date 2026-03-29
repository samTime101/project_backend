from rest_framework import viewsets, permissions
from sql.models import Expense
from .serializers import ExpenseSerializer, ExpenseFilter
from django_filters.rest_framework import DjangoFilterBackend


class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    queryset = Expense.objects.all()
    filterset_class = ExpenseFilter

    def get_queryset(self):
        return Expense.objects.filter(user=self.request.user).order_by('-date', '-id')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    