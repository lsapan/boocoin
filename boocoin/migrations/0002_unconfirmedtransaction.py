# Generated by Django 2.0.3 on 2018-04-02 00:10

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boocoin', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnconfirmedTransaction',
            fields=[
                ('id', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('from_account', models.CharField(db_index=True, max_length=96, null=True)),
                ('to_account', models.CharField(db_index=True, max_length=96)),
                ('coins', models.DecimalField(decimal_places=8, max_digits=20)),
                ('extra_data', models.BinaryField(null=True)),
                ('time', models.DateTimeField()),
                ('signature', models.CharField(max_length=96)),
            ],
        ),
    ]
