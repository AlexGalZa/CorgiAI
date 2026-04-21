READONLY_GROUP = "corgi_readonly"
FULL_ACCESS_GROUP = "corgi_full_access"
ADMIN_GROUP = "corgi_admin"


def _in_group(user, group_name: str) -> bool:
    return user.groups.filter(name=group_name).exists()


def is_corgi_admin(user) -> bool:
    return user.is_superuser or _in_group(user, ADMIN_GROUP)


def is_corgi_full_access(user) -> bool:
    return is_corgi_admin(user) or _in_group(user, FULL_ACCESS_GROUP)


def is_corgi_readonly(user) -> bool:
    return _in_group(user, READONLY_GROUP) and not is_corgi_full_access(user)


class ReadOnlyAdminMixin:
    """
    Mixin that makes a ModelAdmin fully read-only for corgi_readonly group members.
    Full access and admin users retain normal permissions.
    """

    def has_add_permission(self, request):
        if is_corgi_readonly(request.user):
            return False
        return super().has_add_permission(request)

    def has_change_permission(self, request, obj=None):
        if is_corgi_readonly(request.user):
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if is_corgi_readonly(request.user):
            return False
        return super().has_delete_permission(request, obj)
