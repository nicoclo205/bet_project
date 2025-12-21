from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
import secrets

from .models import Usuario, EmailVerificationToken, PasswordResetToken
from .email_service import send_verification_email, send_password_reset_email


@api_view(['POST'])
@permission_classes([AllowAny])
def resend_verification_email(request):
    """
    Resend verification email to user
    """
    try:
        email = request.data.get('email')

        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find user by email
        try:
            usuario = Usuario.objects.get(correo=email)
        except Usuario.DoesNotExist:
            return Response(
                {'error': 'User with this email does not exist'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if already verified
        if usuario.email_verified:
            return Response(
                {'message': 'Email is already verified'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Invalidate old tokens
        EmailVerificationToken.objects.filter(usuario=usuario, is_used=False).update(is_used=True)

        # Generate new verification token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=settings.EMAIL_VERIFICATION_EXPIRATION_HOURS)

        # Create token record
        EmailVerificationToken.objects.create(
            usuario=usuario,
            token=token,
            expires_at=expires_at
        )

        # Send verification email
        send_verification_email(usuario.correo, token, usuario.nombre_usuario)

        return Response(
            {'message': 'Verification email has been sent'},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def verify_email(request):
    """
    Verify user's email with token
    """
    try:
        token = request.data.get('token')

        if not token:
            return Response(
                {'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find token
        try:
            verification_token = EmailVerificationToken.objects.get(token=token)
        except EmailVerificationToken.DoesNotExist:
            return Response(
                {'error': 'Invalid verification token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if token is valid
        if not verification_token.is_valid():
            return Response(
                {'error': 'Verification token has expired or already been used'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Mark email as verified
        usuario = verification_token.usuario
        usuario.email_verified = True
        usuario.save()

        # Mark token as used
        verification_token.is_used = True
        verification_token.save()

        return Response(
            {
                'message': 'Email verified successfully',
                'user': {
                    'id': usuario.id_usuario,
                    'username': usuario.nombre_usuario,
                    'email': usuario.correo,
                    'email_verified': usuario.email_verified
                }
            },
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """
    Request password reset - sends email with reset link
    """
    try:
        email = request.data.get('email')

        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find user by email
        try:
            usuario = Usuario.objects.get(correo=email)
        except Usuario.DoesNotExist:
            # For security, don't reveal if email exists
            return Response(
                {'message': 'If an account exists with this email, a password reset link has been sent'},
                status=status.HTTP_200_OK
            )

        # Invalidate old tokens
        PasswordResetToken.objects.filter(usuario=usuario, is_used=False).update(is_used=True)

        # Generate reset token
        token = secrets.token_urlsafe(32)
        expires_at = timezone.now() + timedelta(hours=settings.PASSWORD_RESET_EXPIRATION_HOURS)

        # Create token record
        PasswordResetToken.objects.create(
            usuario=usuario,
            token=token,
            expires_at=expires_at
        )

        # Send reset email
        try:
            send_password_reset_email(usuario.correo, token, usuario.nombre_usuario)
        except Exception as email_error:
            # Log the error but still return success message for security
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to send password reset email: {str(email_error)}")
            # Delete the token since email failed
            PasswordResetToken.objects.filter(token=token).delete()
            return Response(
                {'error': 'Failed to send email. Please try again later or contact support.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return Response(
            {'message': 'If an account exists with this email, a password reset link has been sent'},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    Reset password using token
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        token = request.data.get('token')
        new_password = request.data.get('new_password')

        if not token or not new_password:
            return Response(
                {'error': 'Token and new password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate password length
        if len(new_password) < 6:
            return Response(
                {'error': 'Password must be at least 6 characters long'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find token
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
        except PasswordResetToken.DoesNotExist:
            return Response(
                {'error': 'Invalid reset token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if token is valid
        if not reset_token.is_valid():
            return Response(
                {'error': 'Reset token has expired or already been used'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Update password
        usuario = reset_token.usuario
        logger.info(f"=== PASSWORD RESET DEBUG ===")
        logger.info(f"User: {usuario.nombre_usuario} (ID: {usuario.id_usuario})")
        logger.info(f"Old Usuario.contrasena hash: {usuario.contrasena[:50]}...")
        logger.info(f"New password (plain): {new_password}")

        # Update Usuario.contrasena (custom field)
        usuario.contrasena = new_password  # Will be hashed by model's save method
        usuario.save()

        # ALSO update Django's User.password (for login authentication)
        if usuario.user:
            logger.info(f"Updating Django User.password for user: {usuario.user.username}")
            usuario.user.set_password(new_password)
            usuario.user.save()
            logger.info(f"Django User.password updated successfully")
        else:
            logger.warning(f"No Django User associated with Usuario {usuario.nombre_usuario}!")

        # Refresh from database to confirm save
        usuario.refresh_from_db()
        logger.info(f"Usuario.contrasena after save: {usuario.contrasena[:50]}...")
        if usuario.user:
            logger.info(f"Django User.password after save: {usuario.user.password[:50]}...")
        logger.info(f"=== END DEBUG ===")

        # Mark token as used
        reset_token.is_used = True
        reset_token.save()

        return Response(
            {'message': 'Password has been reset successfully'},
            status=status.HTTP_200_OK
        )

    except Exception as e:
        logger.error(f"Error resetting password: {str(e)}")
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def validate_reset_token(request):
    """
    Validate if a password reset token is still valid
    """
    try:
        token = request.data.get('token')

        if not token:
            return Response(
                {'error': 'Token is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find token
        try:
            reset_token = PasswordResetToken.objects.get(token=token)
        except PasswordResetToken.DoesNotExist:
            return Response(
                {'valid': False, 'error': 'Invalid token'},
                status=status.HTTP_200_OK
            )

        # Check if token is valid
        if reset_token.is_valid():
            return Response(
                {
                    'valid': True,
                    'username': reset_token.usuario.nombre_usuario,
                    'email': reset_token.usuario.correo
                },
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'valid': False, 'error': 'Token has expired or already been used'},
                status=status.HTTP_200_OK
            )

    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
