from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

from .auth_utils import ensure_designer_access


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None

        user_identifier = (username or "").strip()
        if not user_identifier:
            return None

        UserModel = get_user_model()
        # Fetch all potential matches by username or email (case-insensitive).
        #
        # Legacy/Imported designers may have their email stored on the related
        # DesignerProfile.contact_email field (used for public contact + password reset),
        # so we also allow authentication by that field.
        candidate_users_qs = (
            UserModel.objects.filter(
                Q(username__iexact=user_identifier)
                | Q(email__iexact=user_identifier)
                | Q(designer_profile__contact_email__iexact=user_identifier)
            )
            .distinct()
            .order_by("-is_active", "-last_login", "id")
        )

        # Iterate all candidates and return the first whose password matches
        for candidate_user in candidate_users_qs:
            if candidate_user.check_password(password):
                # Legacy imports can be missing required related rows. Ensure the
                # dashboard prerequisites exist as soon as we have a valid
                # password, so the user can reach their dashboard right away.
                ensure_designer_access(candidate_user)

                # If an account was mistakenly deactivated, allow a successful
                # password-based login to reactivate *designer* accounts (those
                # with a profile) so they can reach the dashboard again.
                if getattr(candidate_user, "is_active", True) is False:
                    if hasattr(candidate_user, "designer_profile"):
                        candidate_user.is_active = True
                        candidate_user.save(update_fields=["is_active"])
                    else:
                        return None

                if not self.user_can_authenticate(candidate_user):
                    return None
                return candidate_user

        # No matching user/password combination found
        return None
