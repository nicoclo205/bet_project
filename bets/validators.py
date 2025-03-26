from django.contrib.auth.models import User
from rest_framework import serializers
import re



def validate_username(value):
    if User.objects.filter(username=value).exists():
        raise serializers.ValidationError("El nombre de usuario ya está en uso")
    if len(value) < 4:
        raise serializers.ValidationError("El nombre de usuario debe tener al menos 4 caracteres")
    return value

def validate_email(value):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(pattern, value):
        raise serializers.ValidationError("El correo electrónico no es válido")

    if User.objects.filter(email=value).exists():
        raise serializers.ValidationError("El correo electrónico ya está en uso")
    
    return value

def validate_password(value):
    if len(value) < 6:
        raise serializers.ValidationError("La contraseña debe tener al menos 6 caracteres")
    return value

def validate_phoneNum(value):
    if len(value) != 10:
        raise serializers.ValidationError("El número de celular debe tener 10 dígitos")
    return value

def validate_name(value):
    if len(value) < 4:
        raise serializers.ValidationError("El nombre debe tener al menos 4 caracteres")
    return value

    if len(value) > 100:
        raise serializers.ValidationError("El nombre no puede tener más de 100 caracteres")
    
    if not value.isalpha():
        raise serializers.ValidationError("El nombre solo puede contener letras")
    
    return value

def validate_lastname(value):
    if len(value) < 4:
        raise serializers.ValidationError("El nombre debe tener al menos 4 caracteres")
    return value

    if len(value) > 100:
        raise serializers.ValidationError("El nombre no puede tener más de 100 caracteres")
    
    if not value.isalpha():
        raise serializers.ValidationError("El nombre solo puede contener letras")
    
    return value