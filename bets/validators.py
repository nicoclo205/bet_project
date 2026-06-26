from django.contrib.auth.models import User
from rest_framework import serializers
import re

# Letras (incluyendo acentos y ñ) más espacios internos
_LETTERS_PATTERN = re.compile(r'^[a-zA-ZáéíóúÁÉÍÓÚüÜñÑ]+([  ][a-zA-ZáéíóúÁÉÍÓÚüÜñÑ]+)*$')


def validate_username(value):
    value = value.strip()
    if len(value) < 4:
        raise serializers.ValidationError("El nombre de usuario debe tener al menos 4 caracteres")
    if User.objects.filter(username=value).exists():
        raise serializers.ValidationError("El nombre de usuario ya está en uso")
    return value


def validate_email(value):
    value = value.strip()
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(pattern, value):
        raise serializers.ValidationError("El correo electrónico no es válido")
    if User.objects.filter(email=value).exists():
        raise serializers.ValidationError("El correo electrónico ya está en uso")
    return value


def validate_password(value):
    # Los espacios al inicio/final no cuentan como caracteres
    if len(value.strip()) < 6:
        raise serializers.ValidationError("La contraseña debe tener al menos 6 caracteres")
    return value


def validate_phoneNum(value):
    # Eliminar espacios y guiones antes de validar
    digits = re.sub(r'[\s\-]', '', value)
    if not digits.isdigit():
        raise serializers.ValidationError("El número de celular solo puede contener dígitos")
    if len(digits) != 10:
        raise serializers.ValidationError("El número de celular debe tener 10 dígitos")
    return digits


def validate_name(value):
    value = value.strip()
    # Los espacios no cuentan para el largo mínimo/máximo
    letters_only = value.replace(' ', '')
    if len(letters_only) < 4:
        raise serializers.ValidationError("El nombre debe tener al menos 4 caracteres")
    if len(letters_only) > 100:
        raise serializers.ValidationError("El nombre no puede tener más de 100 caracteres")
    if not _LETTERS_PATTERN.match(value):
        raise serializers.ValidationError("El nombre solo puede contener letras")
    return value


def validate_lastname(value):
    value = value.strip()
    letters_only = value.replace(' ', '')
    if len(letters_only) < 4:
        raise serializers.ValidationError("El apellido debe tener al menos 4 caracteres")
    if len(letters_only) > 100:
        raise serializers.ValidationError("El apellido no puede tener más de 100 caracteres")
    if not _LETTERS_PATTERN.match(value):
        raise serializers.ValidationError("El apellido solo puede contener letras")
    return value