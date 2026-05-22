from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from sql.models import Expense
from .serializers import ExpenseSerializer, ExpenseFilter, is_locked_transfer_expense
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

    def update(self, request, *args, **kwargs):
        expense = self.get_object()
        if is_locked_transfer_expense(expense):
            return Response(
                {'detail': 'Transfer-generated ledger rows cannot be edited.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        expense = self.get_object()
        if is_locked_transfer_expense(expense):
            return Response(
                {'detail': 'Transfer-generated ledger rows cannot be deleted.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)
