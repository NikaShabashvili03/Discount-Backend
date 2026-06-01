from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('services', '0004_alter_review_unique_together_event_event_ticket'),
    ]

    operations = [
        # Category translation fields
        migrations.AddField(
            model_name='category',
            name='name_en',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='name_ka',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='name_ru',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='name_hi',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='name_ar',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='name_he',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='description_en',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='description_ka',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='description_ru',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='description_hi',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='description_ar',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='category',
            name='description_he',
            field=models.TextField(null=True, blank=True),
        ),

        # City translation fields
        migrations.AddField(
            model_name='city',
            name='name_en',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='city',
            name='name_ka',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='city',
            name='name_ru',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='city',
            name='name_hi',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='city',
            name='name_ar',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='city',
            name='name_he',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),

        # Country translation fields
        migrations.AddField(
            model_name='country',
            name='name_en',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='country',
            name='name_ka',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='country',
            name='name_ru',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='country',
            name='name_hi',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='country',
            name='name_ar',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='country',
            name='name_he',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),

        # Event translation fields
        migrations.AddField(
            model_name='event',
            name='name_en',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='name_ka',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='name_ru',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='name_hi',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='name_ar',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='name_he',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='description_en',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='description_ka',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='description_ru',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='description_hi',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='description_ar',
            field=models.TextField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name='event',
            name='description_he',
            field=models.TextField(null=True, blank=True),
        ),

        # EventImage translation fields
        migrations.AddField(
            model_name='eventimage',
            name='alt_text_en',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='eventimage',
            name='alt_text_ka',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='eventimage',
            name='alt_text_ru',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='eventimage',
            name='alt_text_hi',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='eventimage',
            name='alt_text_ar',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='eventimage',
            name='alt_text_he',
            field=models.CharField(max_length=200, null=True, blank=True),
        ),

        # Discount translation fields
        migrations.AddField(
            model_name='discount',
            name='name_en',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='discount',
            name='name_ka',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='discount',
            name='name_ru',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='discount',
            name='name_hi',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='discount',
            name='name_ar',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='discount',
            name='name_he',
            field=models.CharField(max_length=100, null=True, blank=True),
        ),
    ]
