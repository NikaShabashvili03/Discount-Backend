from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('services', '0005_alter_category_activity'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='adult_price',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Optional adult price', max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='child_price',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Optional child price', max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='infant_price',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Optional infant price', max_digits=10, null=True),
        ),
    ]
