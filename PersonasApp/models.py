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
    organizacion_origen = models.CharField(
        max_length=150, blank=True, null=True, verbose_name="Empresa/Dependencia"
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
