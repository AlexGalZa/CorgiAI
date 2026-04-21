"""
Template tags for feature flags.

Usage in Django templates:
    {% load feature_flags %}

    {% feature_flag "new_portal_dashboard" %}
        <p>New dashboard is enabled!</p>
    {% endfeature_flag %}

    Or with user/org context:
    {% feature_flag "renewal_flow" user=request.user org=current_org %}
        <p>Renewal flow is active.</p>
    {% endfeature_flag %}
"""

from django import template
from common.feature_flags import is_enabled as _is_enabled

register = template.Library()


class FeatureFlagNode(template.Node):
    def __init__(self, flag_key, nodelist, user_var=None, org_var=None):
        self.flag_key = flag_key
        self.nodelist = nodelist
        self.user_var = template.Variable(user_var) if user_var else None
        self.org_var = template.Variable(org_var) if org_var else None

    def render(self, context):
        user = None
        org = None

        if self.user_var:
            try:
                user = self.user_var.resolve(context)
            except template.VariableDoesNotExist:
                pass

        if self.org_var:
            try:
                org = self.org_var.resolve(context)
            except template.VariableDoesNotExist:
                pass

        # Try to get user/org from context if not provided
        if user is None:
            request = context.get("request")
            if request and hasattr(request, "user"):
                user = request.user

        if _is_enabled(self.flag_key, user=user, org=org):
            return self.nodelist.render(context)
        return ""


@register.tag("feature_flag")
def feature_flag_tag(parser, token):
    """
    Block tag that renders its content only when the flag is enabled.

    Syntax:
        {% feature_flag "flag_key" %}
            content
        {% endfeature_flag %}

        {% feature_flag "flag_key" user=request.user org=current_org %}
            content
        {% endfeature_flag %}
    """
    bits = token.split_contents()
    tag_name = bits[0]

    if len(bits) < 2:
        raise template.TemplateSyntaxError(
            f"'{tag_name}' tag requires at least one argument (the flag key)"
        )

    flag_key = bits[1].strip("\"'")
    user_var = None
    org_var = None

    for bit in bits[2:]:
        if bit.startswith("user="):
            user_var = bit[5:]
        elif bit.startswith("org="):
            org_var = bit[4:]

    nodelist = parser.parse(("endfeature_flag",))
    parser.delete_first_token()

    return FeatureFlagNode(
        flag_key=flag_key,
        nodelist=nodelist,
        user_var=user_var,
        org_var=org_var,
    )


@register.simple_tag(takes_context=True)
def feature_flag_enabled(context, flag_key):
    """
    Simple tag that returns True/False for use in {% if %} blocks.

    Usage:
        {% feature_flag_enabled "flag_key" as flag_on %}
        {% if flag_on %}...{% endif %}
    """
    request = context.get("request")
    user = getattr(request, "user", None) if request else None
    return _is_enabled(flag_key, user=user)
