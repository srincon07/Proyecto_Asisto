from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from EstructuraApp.models import Cargo

class Discapacidad(models.Model):
    OPCIONES_ESTADO = [
        ("Activo", "Activo"),
        ("Inactivo", "Inactivo"),
    ]
    nombre_discapacidad = models.CharField(max_length=100, unique=True)
    estado = models.CharField(max_length=20, choices=OPCIONES_ESTADO, default="Activo")

    def __str__(self):
        return self.nombre_discapacidad

    class Meta:
        verbose_name_plural = "Discapacidades"


class Pais(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = "País"
        verbose_name_plural = "Países"


class Region(models.Model):
    pais = models.ForeignKey(Pais, on_delete=models.PROTECT, related_name="regiones")
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre}, {self.pais.nombre}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["pais", "nombre"], name="unique_region_por_pais")
        ]
        verbose_name = "Región"
        verbose_name_plural = "Regiones"


class Ciudad(models.Model):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="ciudades")
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.nombre}, {self.region.nombre}"

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["region", "nombre"], name="unique_ciudad_por_region")
        ]
        verbose_name = "Ciudad"
        verbose_name_plural = "Ciudades"
        

class PersonaManager(BaseUserManager):
    """ Manager personalizado para gestionar la creación de usuarios y superusuarios """
    def create_user(self, email, identificacion, nombres, apellidos, password=None, **extra_fields):
        if not email:
            raise ValueError('El correo electrónico es obligatorio')
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            identificacion=identificacion,
            nombres=nombres,
            apellidos=apellidos,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, identificacion, nombres, apellidos, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser debe tener is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser debe tener is_superuser=True.')

        return self.create_user(email, identificacion, nombres, apellidos, password, **extra_fields)


class Persona(AbstractBaseUser, PermissionsMixin):
    OPCIONES_GENERO = [
        ("Masculino", "Masculino"),
        ("Femenino", "Femenino"),
        ("Otro", "Otro"),
    ]
    OPCIONES_FACTOR_RH = [
        ("O+", "O positivo (O+)"),
        ("O-", "O negativo (O-)"),
        ("A+", "A positivo (A+)"),
        ("A-", "A negativo (A-)"),
        ("B+", "B positivo (B+)"),
        ("B-", "B negativo (B-)"),
        ("AB+", "AB positivo (AB+)"),
        ("AB-", "AB negativo (AB-)"),
    ]

    discapacidad = models.ForeignKey(
        Discapacidad, on_delete=models.CASCADE, null=True, blank=True
    )
    identificacion = models.CharField(max_length=50, unique=True)
    nombres = models.CharField(max_length=255)
    apellidos = models.CharField(max_length=255)
    email = models.EmailField(max_length=254, unique=True)
    telefono = models.CharField(max_length=30, blank=True)
    genero = models.CharField(
        max_length=20, choices=OPCIONES_GENERO, default="Masculino"
    )
    factor_rh = models.CharField(
        max_length=3,
        choices=OPCIONES_FACTOR_RH,
        blank=True,
        verbose_name="Factor RH",
    )
    pais = models.ForeignKey(
        Pais, on_delete=models.PROTECT, null=True, blank=True, related_name="personas"
    )
    region = models.ForeignKey(
        Region, on_delete=models.PROTECT, null=True, blank=True, related_name="personas"
    )
    ciudad = models.ForeignKey(
        Ciudad, on_delete=models.PROTECT, null=True, blank=True, related_name="personas"
    )
    
    # Data Treatment Policy Fields
    autoriza_datos = models.BooleanField(
        default=False,
        verbose_name="Autoriza tratamiento de datos",
        help_text="Indica si la persona autoriza el tratamiento de sus datos personales"
    )
    fecha_autoriza = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de autorización",
        help_text="Fecha y hora en que se otorgó la autorización"
    )
    ip_autoriza = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="IP de autorización",
        help_text="Dirección IP desde la que se otorgó la autorización"
    )
    
    # Control de estado interno de autenticación Django
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False) # Permite el ingreso al backend administrativo
    
    # Relación muchos a muchos usando la tabla intermedia personalizada
    cargos = models.ManyToManyField(
        Cargo, through="PersonaCargo", related_name="personas"
    )
    
    objects = PersonaManager()

    # Configuración de credenciales de Django
    USERNAME_FIELD = 'email'  # El campo con el que se inicia sesión
    REQUIRED_FIELDS = ['identificacion', 'nombres', 'apellidos'] # Campos obligatorios al ejecutar 'createsuperuser'

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"
    
    # Helpers de acceso rápido para control en Vistas de la aplicación
    @property
    def es_admin(self):
        return self.groups.filter(name='Administrador').exists()
    
    @property
    def es_organizador(self):
        return self.groups.filter(name='Organizador').exists()

class PersonaCargo(models.Model):

    OPCIONES_ESTADO = [
        ("Activo", "Activo"),
        ("Inactivo", "Inactivo"),
    ]
    persona = models.ForeignKey(Persona, on_delete=models.CASCADE)
    cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=OPCIONES_ESTADO, default="Activo")

    class Meta:
        unique_together = (
            "persona",
            "cargo",
        )  # Evita duplicar el mismo cargo en la misma persona
