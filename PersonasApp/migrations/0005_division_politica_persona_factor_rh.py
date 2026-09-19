from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("PersonasApp", "0004_remove_persona_organizacion_origen"),
    ]

    operations = [
        migrations.CreateModel(
            name="Pais",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100, unique=True)),
            ],
            options={"verbose_name": "País", "verbose_name_plural": "Países"},
        ),
        migrations.CreateModel(
            name="Region",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100)),
                ("pais", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="regiones", to="PersonasApp.pais")),
            ],
            options={
                "verbose_name": "Región",
                "verbose_name_plural": "Regiones",
                "constraints": [models.UniqueConstraint(fields=("pais", "nombre"), name="unique_region_por_pais")],
            },
        ),
        migrations.CreateModel(
            name="Ciudad",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("nombre", models.CharField(max_length=100)),
                ("region", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="ciudades", to="PersonasApp.region")),
            ],
            options={
                "verbose_name": "Ciudad",
                "verbose_name_plural": "Ciudades",
                "constraints": [models.UniqueConstraint(fields=("region", "nombre"), name="unique_ciudad_por_region")],
            },
        ),
        migrations.AddField(
            model_name="persona",
            name="factor_rh",
            field=models.CharField(blank=True, choices=[("O+", "O positivo (O+)"), ("O-", "O negativo (O-)"), ("A+", "A positivo (A+)"), ("A-", "A negativo (A-)"), ("B+", "B positivo (B+)"), ("B-", "B negativo (B-)"), ("AB+", "AB positivo (AB+)"), ("AB-", "AB negativo (AB-)")], max_length=3, verbose_name="Factor RH"),
        ),
        migrations.AddField(
            model_name="persona",
            name="pais",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="personas", to="PersonasApp.pais"),
        ),
        migrations.AddField(
            model_name="persona",
            name="region",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="personas", to="PersonasApp.region"),
        ),
        migrations.AddField(
            model_name="persona",
            name="ciudad",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="personas", to="PersonasApp.ciudad"),
        ),
    ]