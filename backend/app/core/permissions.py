
from fastapi import Depends, HTTPException, status

from app.api.deps import get_current_user
from app.models.user import User


def require_permissions(*required_codes: str):
    """
    Require the authenticated user to possess every listed permission
    through at least one active role.
    """
    required = {code.strip().upper() for code in required_codes if code.strip()}

    if not required:
        raise ValueError("At least one permission code is required.")

    def permission_checker(
        current_user: User = Depends(get_current_user),
    ) -> User:
        granted_permissions = set()

        for assignment in current_user.user_roles:
            role = assignment.role

            if role is None or not role.is_active:
                continue

            for role_permission in role.role_permissions:
                permission = role_permission.permission

                if permission is not None:
                    granted_permissions.add(permission.code.upper())

        if not required.issubset(granted_permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have the required permission.",
            )

        return current_user

    return permission_checker
