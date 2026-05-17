from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sql', '0006_budget_savingsgoal'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='service_label',
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
