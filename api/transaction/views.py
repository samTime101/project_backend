from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.db import transaction as db_transaction
from sql.models import Transaction, Expense
from .serializers import (
    TransactionResponseSerializer,
    TransactionCreateRequestSerializer,
    TransactionCreateResponseSerializer,
    TransactionRespondRequestSerializer,
    TransactionRespondResponseSerializer,
    TransactionCancelRequestSerializer,
    TransactionCancelResponseSerializer,
)

class TransactionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = TransactionResponseSerializer
    http_method_names = ['get', 'post', 'head', 'options'] 

    def get_queryset(self):
        user = self.request.user
        return Transaction.objects.filter(
            Q(initiator=user) | Q(target=user)
        ).order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return TransactionCreateRequestSerializer
        if self.action == 'respond':
            return TransactionRespondRequestSerializer
        if self.action == 'cancel':
            return TransactionCancelRequestSerializer
        return TransactionResponseSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        transaction = serializer.save()
        response_serializer = TransactionCreateResponseSerializer(transaction,context=self.get_serializer_context(),)
        headers = self.get_success_headers(response_serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    @action(detail=True, methods=['post'])
    def respond(self, request, pk=None):
        trans = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        action_type = serializer.validated_data['action']

        if trans.target != request.user:
            return Response({"error": "Unauthorized."}, status=status.HTTP_403_FORBIDDEN)
        if trans.transaction_type != 'REQUEST' or trans.status != 'PENDING':
            return Response({"error": "Transaction is no longer pending."}, status=status.HTTP_400_BAD_REQUEST)

        with db_transaction.atomic():
            if action_type == 'decline':
                trans.status = 'DECLINED'
            
            elif action_type == 'accept':
                if request.user.balance < trans.amount:
                    return Response({"error": "Insufficient balance."}, status=status.HTTP_400_BAD_REQUEST)
                
                trans.status = 'COMPLETED'
                Expense.objects.create(user=request.user, type='Expense', amount=trans.amount, category='Request Paid')
                Expense.objects.create(user=trans.initiator, type='Income', amount=trans.amount, category='Request Received')
            
            trans.save()
            
        response_serializer = TransactionRespondResponseSerializer(trans,context=self.get_serializer_context(),)
        return Response(response_serializer.data)
    

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        trans = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if trans.initiator != request.user:
            return Response({"error": "Only the initiator can cancel this transaction."}, status=status.HTTP_403_FORBIDDEN)
        if trans.transaction_type != 'REQUEST' or trans.status != 'PENDING':
            return Response({"error": "Only pending requests can be canceled."}, status=status.HTTP_400_BAD_REQUEST)
        trans.status = 'CANCELED'
        trans.save()
        response_serializer = TransactionCancelResponseSerializer(
            trans,
            context=self.get_serializer_context(),
        )
        return Response(response_serializer.data, status=status.HTTP_200_OK)