from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sql', '0009_savingsgoal_image_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='savingsgoal',
            name='image',
            field=models.FileField(blank=True, null=True, upload_to='savings-goals/'),
        ),
    ]
