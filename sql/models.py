from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Sum
from django.conf import settings


class User(AbstractUser):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    username = None
    is_staff = None
    is_superuser = None
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    @property
    def total_expense(self):
        return self.expense_set.filter(type='Expense').aggregate(total=Sum('amount'))['total'] or 0

    @property
    def total_income(self):
        return self.expense_set.filter(type='Income').aggregate(total=Sum('amount'))['total'] or 0

    @property
    def balance(self):
        return self.total_income - self.total_expense


class Expense(models.Model):
    EXPENSE_TYPES = (
        ('Income', 'Income'),
        ('Expense', 'Expense'),
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    type = models.CharField(max_length=10, choices=EXPENSE_TYPES)


class PaymentPlan(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('CANCELED', 'Canceled'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=100)  # "Pay Rent"
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    due_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    created_at = models.DateTimeField(auto_now_add=True)

    def mark_completed(self):
        self.status = 'COMPLETED'
        self.save()
    def complete_with_transaction(self, transaction):
        self.status = 'COMPLETED'
        self.save()
    def __str__(self):
        return f"{self.title} - {self.amount} ({self.status})"


class Transaction(models.Model):
    TRANSACTION_TYPES = (
        ('SEND', 'Send Money'),
        ('REQUEST', 'Request Money'),
    )

    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('DECLINED', 'Declined'),
        ('CANCELED', 'Canceled'),
    )

    initiator = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='initiated_transactions', on_delete=models.CASCADE)
    target = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='targeted_transactions', on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=15, choices=STATUS_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    payment_plan = models.OneToOneField(PaymentPlan, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.transaction_type}: {self.initiator.first_name} & {self.target.first_name} - {self.status}"