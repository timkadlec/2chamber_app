def navlink(title, weight=100, roles=None, group=None):
    def decorator(f):
        f._nav_title = title
        f._nav_weight = weight
        f._nav_roles = roles
        f._nav_group = group
        return f

    return decorator
