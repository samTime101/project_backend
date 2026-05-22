from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sql', '0008_alter_expense_date'),
    ]

    operations = [
        migrations.AddField(
            model_name='savingsgoal',
            name='image_url',
            field=models.URLField(blank=True),
        ),
    ]
