from django.db import models
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from guardian.shortcuts import assign_perm, remove_perm

from TheSum import settings
from TheSum.settings import env
from core.helpers import send_email
from core.models import Assessment, Consultant, Demographic, ViewOnlyAdmin
from django.contrib.auth.models import Group as AuthGroup


# creates the Group for consultants with permissions saved
def create_consultant_group(permissions):
    from django.contrib.auth.models import Group
    new_group, created = Group.objects.get_or_create(name="Consultants")
    for perm in permissions:
        new_group.permissions.add(perm)
    new_group.save()


def create_view_only_admin_group(permissions):
    from django.contrib.auth.models import Group
    from django.contrib.auth.models import Permission
    new_group, created = Group.objects.get_or_create(name="View-Only Admin Group")
    for perm in permissions:
        new_group.permissions.add(perm)
    new_group.permissions.add(Permission.objects.get(codename='view_assessment',
                                                     content_type__app_label='core', content_type__model='assessment'))
    new_group.permissions.add(Permission.objects.get(codename='view_demographic',
                                                     content_type__app_label='core', content_type__model='demographic'))
    new_group.permissions.add(Permission.objects.get(codename='view_user',
                                                     content_type__app_label='core', content_type__model='user'))
    new_group.save()


# Permissions for accessing models can only be set up after migrating
# So, the "post_migrate" signal is required to make this happen
@receiver(post_migrate)
def init_groups(sender, **kwargs):
    from django.contrib.auth.models import Permission
    try:
        permission_list = [
            Permission.objects.get(codename='view_question',
                                   content_type__app_label='core', content_type__model='question'),
            Permission.objects.get(codename='view_score',
                                   content_type__app_label='core', content_type__model='score'),
            Permission.objects.get(codename='view_class_score',
                                   content_type__app_label='core', content_type__model='class_score'),
            Permission.objects.get(codename='view_culture_score',
                                   content_type__app_label='core', content_type__model='culture_score'),
            Permission.objects.get(codename='view_disability_score',
                                   content_type__app_label='core', content_type__model='disability_score'),
            Permission.objects.get(codename='view_gender_score',
                                   content_type__app_label='core', content_type__model='gender_score'),
            Permission.objects.get(codename='view_race_score',
                                   content_type__app_label='core', content_type__model='race_score'),
            Permission.objects.get(codename='view_religion_score',
                                   content_type__app_label='core', content_type__model='religion_score'),
            Permission.objects.get(codename='view_sexual_orientation_score',
                                   content_type__app_label='core', content_type__model='sexual_orientation_score'),
        ]
    except Permission.DoesNotExist:
        return
    create_consultant_group(permission_list)
    create_view_only_admin_group(permission_list)


@receiver(models.signals.post_save, sender=Consultant)
def post_save_consultant_signal_handler(sender, instance, created, **kwargs):
    if created:
        instance.is_staff = True
        group = AuthGroup.objects.get(name="Consultants")
        instance.groups.add(group)
        instance.save()


# View_Only_Admin automatic assigning viewing privileges
@receiver(models.signals.post_save, sender=ViewOnlyAdmin)
def post_save_view_only_admin_signal_handler(sender, instance, created, **kwargs):
    if created:
        instance.is_staff = True
        group = AuthGroup.objects.get(name="View-Only Admin Group")
        instance.groups.add(group)
        instance.save()


@receiver(models.signals.m2m_changed, sender=Assessment.consultants.through)
def assessment_consultant_m2m_changed_signal_handler(sender, instance, action, pk_set, **kwargs):
    # Used for assigning or removing permissions when a assignment-consultant m2m relation is changed
    if action not in ('pre_add', 'pre_remove', 'pre_clear'):
        # ignoring 'post_add', 'post_remove', 'post_clear' to avoid double counting
        return

    # pk_set = set of primary key values that are to be added to the relation
    if instance.__class__ is Consultant:
        consultants = {instance}
        if action == 'pre_clear':
            assessments = {obj for obj in instance.assessment_set.all()}
        else:
            assessments = {Assessment.objects.get(pk=pk) for pk in pk_set}
    else:
        assessments = {instance}
        if action == 'pre_clear':
            consultants = {obj for obj in instance.consultants.all()}
        else:
            consultants = {Consultant.objects.get(pk=pk) for pk in pk_set}

    for consultant in consultants:
        for assessment in assessments:
            demo_obj = Demographic.objects.filter(assessment=assessment).first()
            if action == 'pre_add':
                if assessment not in consultant.assessment_set.all():
                    def send_consultant_email_about_new_assessment():
                        domain = env('APP_URL', default=None)
                        if domain is not None and consultant.email is not None:
                            protocol = settings.PROTOCOL
                            context = dict(protocol=protocol, domain=domain, assessment_pk=assessment.pk,
                                           email_subject="You have been assigned a new assessment")
                            send_email(subject_template_name='core/email_subject.html',
                                       email_template_name='core/consultant_new_assignment_email.html',
                                       context=context,
                                       from_email=settings.FROM_EMAIL,
                                       to_email=consultant.email
                                       )
                    send_consultant_email_about_new_assessment()
                assign_perm('core.view_user', consultant, assessment.user)
                assign_perm('core.view_demographic', consultant, demo_obj)
                assign_perm('core.view_assessment', consultant, assessment)
            elif action == 'pre_clear' or action == 'pre_remove':
                remove_perm('core.view_user', consultant, assessment.user)
                remove_perm('core.view_demographic', consultant, demo_obj)
                remove_perm('core.view_assessment', consultant, assessment)
