from typing import List

from django.core.management import CommandError

from saleor.core.permissions import get_permissions, get_permissions_enum_list


def clean_permissions(required_permissions: List[str]):
    all_permissions = {perm[0]: perm[1] for perm in get_permissions_enum_list()}
    for perm in required_permissions:
        if not all_permissions.get(perm):
            raise CommandError(
                f"Permisssion: {perm} doesn't exist in Saleor."
                f" Avaiable permissions: {all_permissions}"
            )
    return get_permissions(
        [all_permissions[perm] for perm in required_permissions]
    )
