from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0002_simple_review'),
    ]

    operations = [
        # Category translation fields
        migrations.AddField(
            model_name='category',
            name='name_hi',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='description_hi',
            field=models.TextField(null=True, blank=True),
        ),

        # City translation fields
        migrations.AddField(
            model_name='city',
            name='name_hi',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),

        # Country translation fields
        migrations.AddField(
            model_name='country',
            name='name_hi',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),

        # Event translation fields
        migrations.AddField(
            model_name='event',
            name='name_hi',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='description_hi',
            field=models.TextField(null=True, blank=True),
        ),

        # EventImage translation fields
        migrations.AddField(
            model_name='eventimage',
            name='alt_text_hi',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),

        # Discount translation fields
        migrations.AddField(
            model_name='discount',
            name='name_hi',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
    ]
