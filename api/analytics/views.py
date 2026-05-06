from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum
from sql.models import Expense, Budget
from django.utils import timezone
from datetime import timedelta

class AnalyticsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        
        category_data = Expense.objects.filter(user=user, type='Expense').values('category').annotate(total=Sum('amount'))
        
        trends = []
        now = timezone.now()
        for i in range(6):
            month_date = now - timedelta(days=30*i)
            month_start = month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
            
            income = Expense.objects.filter(user=user, type='Income', date__gte=month_start, date__lt=next_month).aggregate(total=Sum('amount'))['total'] or 0
            expense = Expense.objects.filter(user=user, type='Expense', date__gte=month_start, date__lt=next_month).aggregate(total=Sum('amount'))['total'] or 0
            
            trends.append({
                'month': month_start.strftime('%b'),
                'income': float(income),
                'expense': float(expense)
            })
        trends.reverse()

        budgets = Budget.objects.filter(user=user)
        budget_vs_actual = []
        curr_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        for b in budgets:
            actual = Expense.objects.filter(user=user, category=b.category, type='Expense', date__gte=curr_month_start).aggregate(total=Sum('amount'))['total'] or 0
            budget_vs_actual.append({
                'category': b.category,
                'budget': float(b.amount_limit),
                'actual': float(actual)
            })

        return Response({
            'category_distribution': [{'category': item['category'], 'total': float(item['total'])} for item in category_data],
            'monthly_trends': trends,
            'budget_vs_actual': budget_vs_actual
        })
