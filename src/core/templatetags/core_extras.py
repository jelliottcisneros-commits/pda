from django import template
from django.contrib.messages import SUCCESS, ERROR, WARNING

register = template.Library()

message_level_to_bootstrap_alert_dict = {
    SUCCESS: 'alert-success',
    ERROR: 'alert-danger',
    WARNING: 'alert-warning'
}

# source: https://benjaminbaka.wordpress.com/2016/01/23/add-class-attribute-to-django-form-fields/
@register.filter(name='add_class_to_form_field')
def add_class_to_form_field(field, class_attr):
    return field.as_widget(attrs={'class': class_attr})


@register.filter(name='get_bootstrap_alert_class_from_message_level')
def get_bootstrap_alert_class_from_message_level(level):
    return message_level_to_bootstrap_alert_dict.get(level, 'alert-primary')
