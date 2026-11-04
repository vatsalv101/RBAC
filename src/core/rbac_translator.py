"""
Deterministic RBAC Pre-Filter Query Translator
Translates authenticated user roles into cloud vector search filters.
"""
from typing import List, Optional
from qdrant_client.http import models as rest


class RBACTranslator:
    """Translates user role claims into strict vector database pre-filters."""

    @staticmethod
    def build_qdrant_filter(user_roles: List[str]) -> Optional[rest.Filter]:
        """
        Builds the boolean filter condition.
        Returns None for C-Level (unrestricted global access).
        """
        # C-Level has master access: zero restrictions
        if "C-Level" in user_roles:
            return None

        # Standard users: allowed_roles must contain at least one of their assigned roles
        return rest.Filter(
            must=[
                rest.FieldCondition(
                    key="allowed_roles",
                    match=rest.MatchAny(any=user_roles)
                )
            ]
        )

    @staticmethod
    def get_effective_roles(roles: List[str]) -> List[str]:
        """
        Expands user roles according to enterprise hierarchy.
        Every employee automatically inherits the baseline 'Employee' role.
        """
        effective = set(roles)
        if "C-Level" not in effective:
            effective.add("Employee")  # All staff can read employee handbook
        return sorted(list(effective))