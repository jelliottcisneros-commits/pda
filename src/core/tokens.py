from django.contrib.auth.tokens import PasswordResetTokenGenerator

from .models import User, AbstractUser


class TokenGenerator(PasswordResetTokenGenerator):
    """
    Source: https://medium.com/@frfahim/django-registration-with-confirmation-email-bb5da011e4ef
    Source: https://github.com/django/django/blob/45304e444e0d780ceeb5fc03e6761569dfe17ab2/django/contrib/auth/tokens.py
    """

    def _make_hash_value(self, abstract_user: AbstractUser, timestamp):
        # The docs (linked above) say that this value to be hashed, i.e. the return value for this function,
        # must be such that it's value changes after the verification is over.
        if isinstance(abstract_user, User):
            # For the User class after verification is complete can_retake is set to False, so the link becomes invalid
            return str(abstract_user.pk) + str(abstract_user.can_retake) + str(timestamp)
        # For the Unverified User class after verification is complete the unverified_user gets deleted, so the link
        # becomes invalid
        return str(abstract_user.pk) + str(timestamp)


token_generator_for_abstract_user = TokenGenerator()
